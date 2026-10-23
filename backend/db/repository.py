"""Transactional research repository with current snapshots and revision history.

Source publication/fetch dates are nullable and never replaced by ingestion time.
Explicit deletion purges symbol research; ordinary refreshes retain revisions.
"""

import hashlib
import json
import math
import re
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker

from backend.db.models import (
    Base, Article, ArticleCompany, ArticleRevision, CollectionRun, CollectionSourceOutcome,
    Company, CurrentSnapshot, Filing, FilingCompany, FilingRevision, FinancialFact,
    ImportBatch, ResearchNote, SnapshotRevision, Source, Watchlist, WatchlistItem, utcnow,
)

SUPPORTED_SUFFIXES = frozenset({
    "news_sentiment", "comprehensive_news", "sec_sentiment", "sec_filings", "sec_companyfacts",
})
TERMINAL_STATUSES = frozenset({"completed", "partial", "failed"})


def symbol_key(symbol):
    value = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", value):
        raise ValueError("Invalid stock symbol format")
    return value


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def timestamp(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)):
            result = datetime.fromtimestamp(value, tz=timezone.utc)
        elif isinstance(value, datetime):
            result = value
        elif isinstance(value, date):
            result = datetime.combine(value, datetime.min.time())
        elif isinstance(value, str):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def source_time(record, fields):
    return next((parsed for field in fields if (parsed := timestamp(record.get(field))) is not None), None)


def date_value(value):
    parsed = timestamp(value)
    return parsed.date() if parsed else None


def accession_key(value):
    if not isinstance(value, str):
        return None
    compact = value.replace("-", "").strip()
    return f"{compact[:10]}-{compact[10:12]}-{compact[12:]}" if re.fullmatch(r"\d{18}", compact) else None


def validate_snapshot(symbol, suffix, records):
    symbol = symbol_key(symbol)
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("Unsupported research snapshot suffix")
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError("A research snapshot must be a list of objects")
    canonical_json(records)  # Reject nonfinite/non-JSON input before any write.
    return symbol


class ResearchRepository:
    def __init__(self, engine):
        self.engine = engine
        self.session_factory = sessionmaker(engine, expire_on_commit=False)

    def check_ready(self):
        """Verify an explicitly migrated schema, without creating or altering it."""
        with self.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            if not set(Base.metadata.tables).issubset(tables) or "alembic_version" not in tables:
                raise RuntimeError("Database schema is not initialized; run Alembic migrations")
            versions = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
            if versions != {"20261015_02"}:
                raise RuntimeError("Database schema version does not match this application")
        return True

    def _upsert(self, session, model, keys, values):
        dialect = session.bind.dialect.name
        statement = (postgres_insert if dialect == "postgresql" else sqlite_insert)(model).values(**values)
        session.execute(statement.on_conflict_do_nothing(index_elements=keys))
        return session.scalars(select(model).filter_by(**{key: values[key] for key in keys})).one()

    def _insert_rows(self, session, model, rows, keys):
        insert = postgres_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
        for start in range(0, len(rows), 250):
            session.execute(insert(model).values(rows[start:start + 250]).on_conflict_do_nothing(index_elements=keys))

    def _company(self, session, symbol):
        company = self._upsert(session, Company, ["symbol"], {"symbol": symbol})
        # Serializes snapshot publication, watchlist writes, and job creation per symbol.
        return session.scalars(select(Company).where(Company.id == company.id).with_for_update()).one()

    def _watch(self, session, company):
        watchlist = self._upsert(session, Watchlist, ["name"], {"name": "Shared research", "scope": "shared"})
        self._upsert(session, WatchlistItem, ["watchlist_id", "company_id"], {"watchlist_id": watchlist.id, "company_id": company.id})

    def _source(self, session, record, kind, provider=None):
        values = {
            "provider": str(provider or record.get("provider") or "unspecified")[:200],
            "publisher": str(record.get("source") or ("SEC" if kind == "sec" else "unspecified"))[:300],
            "kind": kind,
        }
        return self._upsert(session, Source, ["provider", "publisher", "kind"], values)

    def _article(self, session, company, record):
        source = self._source(session, record, "news")
        published = source_time(record, ("publishedAt", "created_utc", "created", "timestamp"))
        fetched = source_time(record, ("fetched_at", "retrieved_at", "collected_at"))
        url = record.get("url") if isinstance(record.get("url"), str) and record["url"].strip() else None
        title = record.get("title") if isinstance(record.get("title"), str) else None
        identity = ["url", url.strip()] if url else ["article", source.id, title, published.isoformat() if published else None]
        # Titleless, undated rows cannot safely be conflated with other unknown rows.
        if not url and not title:
            identity.append(digest(record))
        article = self._upsert(session, Article, ["identity_hash"], {
            "identity_hash": digest(identity), "source_id": source.id, "url": url,
            "title": title, "published_at": published,
        })
        article.last_seen_at = utcnow()
        self._upsert(session, ArticleCompany, ["article_id", "company_id"], {"article_id": article.id, "company_id": company.id})
        self._upsert(session, ArticleRevision, ["article_id", "content_hash"], {
            "article_id": article.id, "content_hash": digest(record), "payload": record,
            "published_at": published, "fetched_at": fetched,
        })

    def _filing(self, session, company, record, fetched_at=None):
        source = self._source(session, record, "sec", "SEC EDGAR")
        accession = accession_key(record.get("accession_number") or record.get("accession"))
        url = record.get("url") or record.get("filing_url")
        form = record.get("form_type") or record.get("form")
        filed = date_value(record.get("filing_date") or record.get("filed"))
        identity = ["accession", accession] if accession else ["filing", company.id, url, form, str(filed)]
        if not accession and not url:
            identity.append(digest(record))
        filing = self._upsert(session, Filing, ["identity_hash"], {
            "identity_hash": digest(identity), "accession_number": accession,
            "company_id": company.id, "source_id": source.id, "url": url,
            "form_type": str(form)[:30] if form else None, "filing_date": filed,
            "report_period": date_value(record.get("report_date") or record.get("report_period")),
            "accepted_at": timestamp(record.get("acceptance_datetime") or record.get("accepted_at")),
            "is_amendment": bool(form and str(form).endswith("/A")),
        })
        self._upsert(session, FilingCompany, ["filing_id", "company_id"], {"filing_id": filing.id, "company_id": company.id})
        self._upsert(session, FilingRevision, ["filing_id", "content_hash"], {
            "filing_id": filing.id, "content_hash": digest(record), "payload": record,
            "fetched_at": source_time(record, ("fetched_at", "retrieved_at", "collected_at")) or fetched_at,
        })
        return filing

    def _sec_facts(self, session, company, envelope):
        cik = str(envelope.get("cik") or "").strip()
        if cik.isdigit() and len(cik) <= 10:
            company.cik = cik.zfill(10)
        if isinstance(envelope.get("entity_name"), str):
            company.name = envelope["entity_name"]
        metadata = envelope.get("metadata") or {}
        fetched = source_time(metadata, ("retrieved_at", "collected_at"))
        filings = {row.accession_number: row for row in session.scalars(
            select(Filing).join(FilingCompany).where(FilingCompany.company_id == company.id)
        ) if row.accession_number}
        for row in envelope.get("filings", []):
            filing = self._filing(session, company, row, fetched)
            if filing.accession_number:
                filings[filing.accession_number] = filing
        source = self._source(session, {}, "sec", "SEC EDGAR")
        # Read identities/versions once and batch inserts: Company Facts can contain
        # thousands of observations, so a database round trip per fact is too costly.
        existing = session.execute(select(
            FinancialFact.identity_hash, FinancialFact.namespace, FinancialFact.concept,
            FinancialFact.unit, FinancialFact.period_start, FinancialFact.period_end,
            FinancialFact.version,
        ).where(FinancialFact.company_id == company.id)).all()
        identities = {row.identity_hash for row in existing}
        versions = {}
        for row in existing:
            key = (row.namespace, row.concept, row.unit, row.period_start, row.period_end)
            versions[key] = max(versions.get(key, 0), row.version)
        inserts = []
        for row in envelope.get("facts", []):
            identity_hash = digest([company.id, row.get("fact_id") or digest(row)])
            if identity_hash in identities:
                continue
            identities.add(identity_hash)
            accession = accession_key(row.get("accession"))
            filing = filings.get(accession)
            if accession and filing is None:
                filing_record = {key: row.get(key) for key in ("accession", "form", "filed", "filing_url")}
                filing = self._filing(session, company, filing_record, fetched)
                filings[accession] = filing
            period_start, period_end = date_value(row.get("start")), date_value(row.get("end"))
            # Invalid source periods remain in raw evidence, rather than violating normalized constraints.
            if period_start and period_end and period_start > period_end:
                period_start = None
            concept = str(row.get("concept") or "unspecified")
            unit = str(row.get("unit") or "unspecified")
            namespace = str(row.get("taxonomy") or "unspecified")
            key = (namespace, concept, unit, period_start, period_end)
            versions[key] = versions.get(key, 0) + 1
            value = row.get("value")
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                value = None
            kind = row.get("period_kind")
            inserts.append({
                "identity_hash": identity_hash, "company_id": company.id,
                "filing_id": filing.id if filing else None, "source_id": source.id,
                "namespace": namespace, "concept": concept, "unit": unit, "value": value,
                "period_start": period_start, "period_end": period_end,
                "period_type": kind if kind in {"instant", "duration"} else "unknown",
                "fiscal_year": row.get("fiscal_year"), "fiscal_period": row.get("fiscal_period"),
                "filed_at": date_value(row.get("filed")), "version": versions[key],
                "is_amendment": str(row.get("form") or "").endswith("/A"), "payload": row,
            })
        self._insert_rows(session, FinancialFact, inserts, ["identity_hash"])

    def _save(self, session, symbol, suffix, records, import_batch_id=None):
        company = self._company(session, symbol)
        self._watch(session, company)
        revision = self._upsert(session, SnapshotRevision, ["company_id", "suffix", "content_hash"], {
            "company_id": company.id, "suffix": suffix, "content_hash": digest(records),
            "payload": records, "import_batch_id": import_batch_id,
        })
        for record in records:
            if suffix == "sec_companyfacts":
                self._sec_facts(session, company, record)
            elif suffix in {"sec_sentiment", "sec_filings"}:
                self._filing(session, company, record)
            else:
                self._article(session, company, record)
        current = self._upsert(session, CurrentSnapshot, ["company_id", "suffix"], {
            "company_id": company.id, "suffix": suffix, "revision_id": revision.id,
        })
        current.revision_id, current.updated_at = revision.id, utcnow()
        return f"db://snapshot/{revision.id}"

    def save_snapshot(self, symbol, suffix, records):
        symbol = validate_snapshot(symbol, suffix, records)
        with self.session_factory.begin() as session:
            return self._save(session, symbol, suffix, records)

    def load_snapshots(self, symbol, suffixes=None):
        """Read only requested current payloads; financial snapshots can be large."""
        symbol = symbol_key(symbol)
        statement = select(CurrentSnapshot.suffix, SnapshotRevision.payload).join(
            Company, Company.id == CurrentSnapshot.company_id,
        ).join(SnapshotRevision, SnapshotRevision.id == CurrentSnapshot.revision_id).where(
            Company.symbol == symbol,
        )
        if suffixes is not None:
            suffixes = tuple(dict.fromkeys(suffixes))
            if any(suffix not in SUPPORTED_SUFFIXES for suffix in suffixes):
                raise ValueError("Unsupported research snapshot suffix")
            statement = statement.where(CurrentSnapshot.suffix.in_(suffixes))
        with self.session_factory() as session:
            rows = session.execute(statement.order_by(CurrentSnapshot.suffix)).all()
            return [(suffix, payload) for suffix, payload in rows]

    def read_snapshot_reference(self, reference):
        prefix = "db://snapshot/"
        if not isinstance(reference, str) or not reference.startswith(prefix):
            raise ValueError("Invalid database snapshot reference")
        try:
            revision_id = str(UUID(reference[len(prefix):]))
        except (ValueError, TypeError):
            raise ValueError("Invalid database snapshot reference") from None
        with self.session_factory() as session:
            revision = session.get(SnapshotRevision, revision_id)
            if revision is None:
                raise KeyError("Snapshot reference does not exist")
            return revision.payload

    def list_symbols(self):
        with self.session_factory() as session:
            return list(session.scalars(select(Company.symbol).join(WatchlistItem).distinct().order_by(Company.symbol)))

    def delete_symbol_research(self, symbol):
        symbol = symbol_key(symbol)
        with self.session_factory.begin() as session:
            company = session.scalars(select(Company).where(Company.symbol == symbol).with_for_update()).first()
            if company is None:
                return []
            active = session.scalar(select(CollectionRun.id).where(CollectionRun.company_id == company.id, CollectionRun.status.in_(["pending", "processing"])))
            if active:
                raise ValueError("Cannot delete research while a collection run is active")
            references = [f"db://snapshot/{value}" for value in session.scalars(select(SnapshotRevision.id).where(SnapshotRevision.company_id == company.id))]
            article_ids = list(session.scalars(select(ArticleCompany.article_id).where(ArticleCompany.company_id == company.id)))
            filing_ids = list(session.scalars(select(FilingCompany.filing_id).where(FilingCompany.company_id == company.id)))
            session.execute(delete(CurrentSnapshot).where(CurrentSnapshot.company_id == company.id))
            session.execute(delete(SnapshotRevision).where(SnapshotRevision.company_id == company.id))
            session.execute(delete(WatchlistItem).where(WatchlistItem.company_id == company.id))
            session.execute(delete(ResearchNote).where(ResearchNote.company_id == company.id))
            run_ids = select(CollectionRun.id).where(CollectionRun.company_id == company.id)
            session.execute(delete(CollectionSourceOutcome).where(CollectionSourceOutcome.run_id.in_(run_ids)))
            session.execute(delete(CollectionRun).where(CollectionRun.company_id == company.id))
            session.execute(delete(FinancialFact).where(FinancialFact.company_id == company.id))
            session.execute(delete(ArticleCompany).where(ArticleCompany.company_id == company.id))
            session.execute(delete(FilingCompany).where(FilingCompany.company_id == company.id))
            for article_id in article_ids:
                if not session.scalar(select(ArticleCompany.article_id).where(ArticleCompany.article_id == article_id).limit(1)):
                    session.execute(delete(ArticleRevision).where(ArticleRevision.article_id == article_id))
                    session.execute(delete(Article).where(Article.id == article_id))
            for filing_id in filing_ids:
                if not session.scalar(select(FilingCompany.filing_id).where(FilingCompany.filing_id == filing_id).limit(1)):
                    session.execute(delete(FilingRevision).where(FilingRevision.filing_id == filing_id))
                    session.execute(delete(Filing).where(Filing.id == filing_id))
            return references

    def import_snapshots(self, snapshots, manifest_hash):
        """Apply an entire validated manifest in one transaction; repeated manifests do nothing."""
        prepared = [(validate_snapshot(symbol, suffix, records), suffix, records) for symbol, suffix, records in snapshots]
        with self.session_factory.begin() as session:
            existing = session.scalar(select(ImportBatch).where(ImportBatch.manifest_hash == manifest_hash))
            if existing:
                return {"batch_id": existing.id, "applied": False, "files": existing.file_count, "records": existing.record_count}
            insert = postgres_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
            inserted_id = session.execute(insert(ImportBatch).values(
                manifest_hash=manifest_hash, file_count=len(prepared),
                record_count=sum(len(records) for _, _, records in prepared),
            ).on_conflict_do_nothing(index_elements=["manifest_hash"]).returning(ImportBatch.id)).scalar_one_or_none()
            batch = session.scalar(select(ImportBatch).where(ImportBatch.manifest_hash == manifest_hash))
            if inserted_id is None:
                return {"batch_id": batch.id, "applied": False, "files": batch.file_count, "records": batch.record_count}
            for symbol, suffix, records in sorted(prepared, key=lambda item: item[:2]):
                self._save(session, symbol, suffix, records, batch.id)
            return {"batch_id": batch.id, "applied": True, "files": batch.file_count, "records": batch.record_count}

    def _run_dict(self, session, run, created=None):
        company = session.get(Company, run.company_id)
        outcomes = session.scalars(select(CollectionSourceOutcome).where(CollectionSourceOutcome.run_id == run.id)).all()
        result = {
            "run_id": run.id, "symbol": company.symbol, "status": run.status,
            "progress": run.progress, "message": run.message,
            "started_at": timestamp(run.started_at), "completed_at": timestamp(run.completed_at),
            "providers": {row.source_name: {"status": row.status, "count": row.record_count, "message": row.message} for row in outcomes},
        }
        if created is not None:
            result["created"] = created
        return result

    def create_run(self, symbol, sources):
        symbol = symbol_key(symbol)
        with self.session_factory.begin() as session:
            company = self._company(session, symbol)
            active = session.scalar(select(CollectionRun).where(CollectionRun.company_id == company.id, CollectionRun.status.in_(["pending", "processing"])).order_by(CollectionRun.started_at.desc()))
            if active:
                return self._run_dict(session, active, False)
            run = CollectionRun(company_id=company.id, status="pending", progress=0, message="Research refresh queued", requested_sources=list(dict.fromkeys(sources)))
            session.add(run)
            session.flush()
            return self._run_dict(session, run, True)

    def update_run(self, run_id, *, status, progress, message, providers=None):
        if status not in TERMINAL_STATUSES | {"pending", "processing"} or not 0 <= progress <= 100:
            raise ValueError("Invalid collection run state")
        with self.session_factory.begin() as session:
            run = session.scalar(select(CollectionRun).where(CollectionRun.id == run_id).with_for_update())
            if run is None:
                raise KeyError("Collection run does not exist")
            if run.status in TERMINAL_STATUSES and status != run.status:
                raise ValueError("A finished collection run cannot be restarted")
            run.status, run.progress, run.message, run.updated_at = status, progress, message, utcnow()
            if status in TERMINAL_STATUSES and run.completed_at is None:
                run.completed_at = utcnow()
            for name, outcome in (providers or {}).items():
                count = outcome.get("count", 0)
                if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    raise ValueError("Invalid source record count")
                row = self._upsert(session, CollectionSourceOutcome, ["run_id", "source_name"], {
                    "run_id": run.id, "source_name": name, "status": outcome["status"],
                    "record_count": count, "message": outcome.get("message", ""),
                })
                row.status, row.record_count, row.message, row.updated_at = outcome["status"], count, outcome.get("message", ""), utcnow()
            session.flush()
            return self._run_dict(session, run)

    def get_run(self, run_id):
        with self.session_factory() as session:
            run = session.get(CollectionRun, run_id)
            return self._run_dict(session, run) if run else None

    def get_latest_run(self, symbol):
        with self.session_factory() as session:
            run = session.scalar(select(CollectionRun).join(Company).where(Company.symbol == symbol_key(symbol)).order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc()).limit(1))
            return self._run_dict(session, run) if run else None

    def interrupt_active_runs(self):
        """Explicit single-worker startup recovery; never call from each web worker."""
        with self.session_factory.begin() as session:
            runs = session.scalars(select(CollectionRun).where(CollectionRun.status.in_(["pending", "processing"])).with_for_update()).all()
            for run in runs:
                run.status, run.progress = "failed", 100
                run.message = "Collection interrupted by service restart; start a new refresh"
                run.updated_at = run.completed_at = utcnow()
            return len(runs)
