"""Offline SQLite tests exercise repository transactions and explicit migrations."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text

from backend.db import ResearchRepository, get_repository
from backend.db.engine import create_database_engine
from backend.db.models import (
    Article, ArticleCompany, ArticleRevision, Base, CollectionRun, Company,
    CurrentSnapshot, Filing, FilingCompany, FilingRevision, FinancialFact,
    ImportBatch, SnapshotRevision,
)
from scripts.import_research import inspect_directory, main

ROOT = Path(__file__).resolve().parents[2]


def migrate(engine, revision="head"):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


@pytest.fixture
def repository():
    engine = create_database_engine("sqlite://", allow_sqlite=True)
    migrate(engine)
    yield ResearchRepository(engine)
    engine.dispose()


def count(repository, model):
    with repository.session_factory() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_configuration_does_not_enable_sqlite_or_fallback_on_bad_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_repository() is None
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    with pytest.raises(ValueError, match="PostgreSQL"):
        get_repository()
    monkeypatch.setenv("DATABASE_URL", "not a URL: secret-value")
    with pytest.raises(ValueError, match="valid database") as raised:
        get_repository()
    assert "secret-value" not in str(raised.value)


def test_configuration_never_auto_creates_schema():
    engine = create_database_engine("sqlite://", allow_sqlite=True)
    repository = ResearchRepository(engine)
    with pytest.raises(RuntimeError, match="migrations"):
        repository.check_ready()
    assert inspect(engine).get_table_names() == []
    engine.dispose()


def test_explicit_migration_matches_models_and_schema_version(repository):
    assert repository.check_ready() is True
    assert set(Base.metadata.tables).issubset(inspect(repository.engine).get_table_names())
    with repository.engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='other'"))
    with pytest.raises(RuntimeError, match="version"):
        repository.check_ready()


def test_snapshot_revisions_are_immutable_and_identical_writes_are_idempotent(repository):
    original = [{"url": "https://example.org/a", "title": "Original", "publishedAt": "2020-01-01T12:00:00Z"}]
    first = repository.save_snapshot("aapl", "news_sentiment", original)
    assert first.startswith("db://snapshot/")
    assert repository.save_snapshot("AAPL", "news_sentiment", original) == first
    revised = [{**original[0], "title": "Corrected"}]
    second = repository.save_snapshot("AAPL", "news_sentiment", revised)
    assert first != second
    assert repository.load_snapshots("AAPL") == [("news_sentiment", revised)]
    assert repository.read_snapshot_reference(first) == original
    assert repository.list_symbols() == ["AAPL"]
    assert count(repository, SnapshotRevision) == count(repository, ArticleRevision) == 2
    assert count(repository, Article) == 1
    with repository.session_factory() as session:
        article = session.scalar(select(Article))
        revision = session.scalar(select(ArticleRevision).order_by(ArticleRevision.observed_at))
        assert article.published_at.year == 2020
        assert article.first_seen_at.year >= 2026
        assert revision.fetched_at is None


def test_invalid_snapshot_cannot_publish_partial_data(repository):
    with pytest.raises(ValueError):
        repository.save_snapshot("AAPL", "news_sentiment", [{"title": "Okay"}, {"score": float("nan")}])
    assert repository.list_symbols() == []
    assert count(repository, SnapshotRevision) == count(repository, Company) == 0
    with pytest.raises(ValueError):
        repository.save_snapshot("AAPL", "reddit_sentiment", [{"title": "Unsupported"}])
    with pytest.raises(ValueError):
        repository.read_snapshot_reference("/some/private/path")


def test_explicit_delete_purges_archives_but_preserves_shared_articles(repository):
    common = {"url": "https://example.org/shared", "title": "Industry news"}
    old = repository.save_snapshot("AAPL", "news_sentiment", [common])
    repository.save_snapshot("AAPL", "news_sentiment", [common, {"title": "Only AAPL"}])
    other = repository.save_snapshot("MSFT", "news_sentiment", [common])
    removed = repository.delete_symbol_research("AAPL")
    assert old in removed
    assert repository.load_snapshots("AAPL") == []
    assert repository.list_symbols() == ["MSFT"]
    with pytest.raises(KeyError):
        repository.read_snapshot_reference(old)
    assert repository.read_snapshot_reference(other) == [common]
    assert count(repository, Article) == count(repository, ArticleRevision) == count(repository, ArticleCompany) == 1
    assert repository.delete_symbol_research("MSFT") == [other]
    assert count(repository, Article) == 0


def test_sec_facts_preserve_versions_units_missing_periods_and_accessions(repository):
    filed = {"accession": "0000320193-26-000001", "form": "10-K", "filed": "2026-01-01", "filing_url": "https://www.sec.gov/filing"}
    fact = {**filed, "fact_id": "first", "taxonomy": "us-gaap", "concept": "Revenue", "unit": "USD", "value": 0, "start": "2025-01-01", "end": "2025-12-31", "period_kind": "duration"}
    second = {**fact, "fact_id": "second", "accession": "0000320193-26-000002", "form": "10-K/A", "value": 12}
    unknown = {"fact_id": "unknown", "taxonomy": "us-gaap", "concept": "Assets", "unit": "USD", "value": None, "period_kind": "unknown"}
    envelope = {"cik": "320193", "entity_name": "Example", "facts": [fact, second, unknown], "filings": [filed], "metadata": {"retrieved_at": "2026-01-03T10:00:00Z"}}
    repository.save_snapshot("AAPL", "sec_companyfacts", [envelope])
    repository.save_snapshot("AAPL", "sec_companyfacts", [envelope])
    assert count(repository, FinancialFact) == 3
    assert count(repository, Filing) == 2
    with repository.session_factory() as session:
        facts = session.scalars(select(FinancialFact).where(FinancialFact.concept == "Revenue").order_by(FinancialFact.version)).all()
        assert [row.version for row in facts] == [1, 2]
        assert facts[0].value == 0 and facts[1].is_amendment
        assert facts[0].unit == "USD" and facts[0].payload == fact
        unknown_fact = session.scalar(select(FinancialFact).where(FinancialFact.concept == "Assets"))
        assert unknown_fact.period_end is None and unknown_fact.value is None
        assert session.scalar(select(Company.cik)) == "0000320193"
    repository.delete_symbol_research("AAPL")
    for model in (FinancialFact, Filing, FilingCompany, FilingRevision, SnapshotRevision):
        assert count(repository, model) == 0


def test_shared_filing_accession_is_deduplicated_across_symbols(repository):
    row = {"accession_number": "000032019326000001", "form_type": "10-K", "filing_date": "2026-01-01"}
    repository.save_snapshot("AAPL", "sec_filings", [row])
    repository.save_snapshot("MSFT", "sec_filings", [{**row, "accession_number": "0000320193-26-000001"}])
    assert count(repository, Filing) == 1
    assert count(repository, FilingCompany) == 2
    repository.delete_symbol_research("AAPL")
    assert count(repository, Filing) == 1
    repository.delete_symbol_research("MSFT")
    assert count(repository, Filing) == 0


def test_durable_jobs_deduplicate_and_keep_partial_provider_results(repository):
    first = repository.create_run("AAPL", ["news", "sec"])
    assert first["created"]
    second = repository.create_run("AAPL", ["news"])
    assert second["run_id"] == first["run_id"] and not second["created"]
    with pytest.raises(ValueError, match="active"):
        repository.delete_symbol_research("AAPL")
    providers = {"news": {"status": "completed", "count": 2, "message": "Collected"}, "sec": {"status": "failed", "count": 0, "message": "Unavailable"}}
    done = repository.update_run(first["run_id"], status="partial", progress=100, message="Partial result", providers=providers)
    assert done["completed_at"] is not None
    assert ResearchRepository(repository.engine).get_latest_run("AAPL")["providers"] == providers
    with pytest.raises(ValueError, match="finished"):
        repository.update_run(first["run_id"], status="processing", progress=1, message="Cannot restart")
    repository.create_run("MSFT", ["news"])
    assert repository.interrupt_active_runs() == 1
    assert repository.get_latest_run("MSFT")["status"] == "failed"
    assert repository.get_run(first["run_id"])["status"] == "partial"
    repository.delete_symbol_research("AAPL")
    assert repository.get_latest_run("AAPL") is None


def test_import_dry_run_is_read_only_skips_legacy_and_reruns_idempotently(repository, tmp_path, monkeypatch, capsys):
    path = tmp_path / "AAPL_news_sentiment.json"
    path.write_text(json.dumps([{"title": "Original", "publishedAt": "2020-01-01"}]))
    (tmp_path / "AAPL_reddit_sentiment.json").write_text("not even JSON")
    before = path.read_bytes()
    monkeypatch.setenv("DATABASE_URL", "intentionally-invalid-no-connection")
    assert main(["--data-dir", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"mode": "dry_run", "files": 1, "records": 1, "skipped_files": 1, "writes": 0}
    snapshots, manifest, _ = inspect_directory(tmp_path)
    assert repository.import_snapshots(snapshots, manifest)["applied"]
    assert not repository.import_snapshots(snapshots, manifest)["applied"]
    assert count(repository, ImportBatch) == 1
    assert path.read_bytes() == before
    path.write_text(json.dumps([{"title": "Corrected", "publishedAt": "2020-01-01"}]))
    snapshots, manifest, _ = inspect_directory(tmp_path)
    assert repository.import_snapshots(snapshots, manifest)["applied"]
    assert count(repository, ImportBatch) == count(repository, SnapshotRevision) == 2


def test_import_transaction_rolls_back_all_files_on_normalization_failure(repository):
    snapshots = [("AAPL", "news_sentiment", [{"title": "Valid"}]), ("MSFT", "sec_companyfacts", [{"facts": [None]}])]
    with pytest.raises((AttributeError, TypeError)):
        repository.import_snapshots(snapshots, "fixture-batch")
    assert repository.list_symbols() == []
    assert count(repository, SnapshotRevision) == count(repository, ImportBatch) == count(repository, Company) == 0


def test_import_rejects_invalid_json_before_apply_and_never_echoes_secrets(tmp_path, capsys):
    (tmp_path / "AAPL_news_sentiment.json").write_text('[{"password":"fixture-secret","value":NaN}]')
    assert main(["--data-dir", str(tmp_path), "--apply"]) == 1
    assert "fixture-secret" not in capsys.readouterr().out


def test_large_fact_snapshot_is_idempotent_and_preserves_every_observation(repository):
    facts = [{
        "fact_id": f"fixture-{index}", "taxonomy": "us-gaap", "concept": "Revenue",
        "unit": "USD", "value": index, "start": "2025-01-01", "end": "2025-12-31",
        "period_kind": "duration", "accession": "0000320193-26-000001", "form": "10-K",
    } for index in range(1001)]
    envelope = [{"facts": facts, "filings": []}]
    first = repository.save_snapshot("AAPL", "sec_companyfacts", envelope)
    assert repository.save_snapshot("AAPL", "sec_companyfacts", envelope) == first
    assert count(repository, FinancialFact) == 1001
    assert count(repository, Filing) == count(repository, FilingRevision) == 1
    with repository.session_factory() as session:
        assert session.scalar(select(func.max(FinancialFact.version))) == 1001


def test_supabase_connection_requires_tls_without_opening_a_connection():
    engine = create_database_engine("postgresql://fixture@aws-0.example.pooler.supabase.com/fixture?sslmode=disable")
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.url.query["sslmode"] == "require"
    engine.dispose()


def test_filtered_snapshot_reads_exclude_unrelated_financial_payloads(repository):
    news = [{"title": "News"}]
    financial = [{"facts": [], "filings": [], "metadata": {"marker": "large-financial-payload"}}]
    repository.save_snapshot("AAPL", "news_sentiment", news)
    repository.save_snapshot("AAPL", "sec_companyfacts", financial)
    assert repository.load_snapshots("AAPL", ["news_sentiment"]) == [("news_sentiment", news)]
    assert repository.load_snapshots("AAPL", ["sec_companyfacts"]) == [("sec_companyfacts", financial)]
    assert repository.load_snapshots("AAPL", []) == []
    assert len(repository.load_snapshots("AAPL")) == 2
    with pytest.raises(ValueError, match="Unsupported"):
        repository.load_snapshots("AAPL", ["unsupported"])


def test_news_evidence_and_fact_readers_request_only_relevant_snapshot_types(monkeypatch):
    from backend.services import research
    class RecordingRepository:
        def __init__(self):
            self.requests = []
        def load_snapshots(self, symbol, suffixes=None):
            self.requests.append((symbol, set(suffixes)))
            return []
    repository = RecordingRepository()
    monkeypatch.setattr(research, "repository", lambda: repository)
    research.saved_news("AAPL")
    research.load_evidence("AAPL")
    research.saved_sec_facts("AAPL")
    assert repository.requests == [
        ("AAPL", {"news_sentiment", "comprehensive_news"}),
        ("AAPL", {"news_sentiment", "comprehensive_news", "sec_sentiment", "sec_filings"}),
        ("AAPL", {"sec_companyfacts"}),
    ]


def test_file_snapshot_filter_does_not_open_unrequested_facts(monkeypatch, tmp_path):
    from backend.services import research
    monkeypatch.setattr(research, "repository", lambda: None)
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path))
    (tmp_path / "AAPL_news_sentiment.json").write_text('[{"title":"News"}]')
    facts_path = tmp_path / "AAPL_sec_companyfacts.json"
    facts_path.write_text('[{"facts":[]}]')
    original = Path.read_text
    def read_text(path, *args, **kwargs):
        assert path != facts_path, "Unrequested financial payload should not be read"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read_text)
    assert research.saved_news("AAPL") == [{"title": "News"}]


def test_postgres_connections_have_bounded_waits(monkeypatch):
    captured = {}
    def capture(url, **kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setattr('backend.db.engine.create_engine', capture)
    create_database_engine('postgresql://user:password@localhost/research')
    assert captured['pool_timeout'] == 10
    args = captured['connect_args']
    assert args['connect_timeout'] == 8
    assert args['keepalives'] == 1
    assert args['tcp_user_timeout'] == 15000
    assert 'statement_timeout=30000' in args['options']
