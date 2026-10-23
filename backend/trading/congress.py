"""Disclosure imports retain dates and provenance; no inferred original trade prices."""
from __future__ import annotations

import csv
import hashlib
import io
from functools import lru_cache
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from backend.services.research import normalized_symbol
from backend.trading.market import market_today

COLUMNS = ["disclosure_id", "member", "owner", "symbol", "side", "transaction_date", "available_date", "asset_type", "amount_range", "source_url"]

PROVENANCE_LIMITATIONS = [
    "Coverage is limited to imported transaction rows; no live Congress feed is connected.",
    "Dates, classifications, owners, and public availability are user-supplied and not independently verified; source links are retained but not fetched.",
    "Reported amounts are ranges. Counts and disclosure lags do not describe exact holdings, allocations, or investment returns.",
    "Amendments are not supported. Member summaries include all imported household owners and asset types, including options and other assets that cannot be copied in backtests.",
]

AUTOMATIC_LIMITATIONS = [
    "Automatic coverage is a third-party normalization of official House and Senate disclosures, not a complete or real-time official feed. Review each original filing.",
    "Automatic availability dates are publisher estimates based on the end of the filing day in New York, not independently verified publication timestamps. StockScope first-observed times are retained separately.",
    "Reported amounts are ranges. Counts and reported lags do not establish holdings, allocations, or investment returns. Missing tickers and unsupported actions are excluded with coverage counts.",
    "Browse shows the latest available event version; tests use the original eligible version once and do not copy later corrections as additional trades. Unknown assets and options are excluded from copying.",
]


def _evidence_key(row):
    """Avoid copying a manually imported row again when the same evidence is collected."""
    source = urlsplit(row["source_url"])
    owner = row["owner"].strip().casefold()
    owner = {"self": "member", "sp": "spouse", "joint": "joint", "jt": "joint", "dc": "dependent child", "dependent": "dependent child", "dependent_child": "dependent child"}.get(owner, owner)
    return (source.hostname, source.path.rstrip("/"), row["symbol"], row["side"],
            row["transaction_date"], owner, row["amount_range"].replace(" ", "").replace(",", ""))


@lru_cache(maxsize=1)
def _successful_feed(storage_identity, source_revision, data_revision):
    # Only cache a completed immutable snapshot; job status is always read fresh.
    from backend.trading import storage
    return storage.read("congress-feed") or {"records": []}


def research_document(*, original_versions=False):
    """Join manual evidence with collected versions without changing either store."""
    from backend.trading import storage, disclosure_collector
    from backend.services import research
    manual = storage.read("congress") or {"records": []}
    collection = disclosure_collector.status()
    if collection.get("last_success"):
        repo = research.repository()
        identity = repo.engine if repo is not None else str(research.data_directory().resolve())
        feed = _successful_feed(identity, collection.get("source", {}).get("revision"), collection.get("data_revision", 0))
    else:
        feed = storage.read("congress-feed") or {"records": []}
    groups = {}
    for row in feed.get("records", []):
        groups.setdefault(row["event_id"], []).append(row)
    automatic = []
    for versions in groups.values():
        record = (min if original_versions else max)(versions, key=lambda row: row["version"])
        if original_versions:
            # A corrected version cannot manufacture an otherwise missing original signal.
            if record["version"] != 1 or record.get("is_amendment"):
                continue
        elif record.get("superseded_at"):
            continue
        automatic.append(record)
    keys = {_evidence_key(row) for row in automatic}
    manual_rows = [row for row in manual["records"] if _evidence_key(row) not in keys]
    records = sorted([*manual_rows, *automatic], key=lambda row: (row["available_date"], row["transaction_date"], row["disclosure_id"]))
    return {"records": records, "last_import": manual.get("last_import"),
            "collection": collection, "automatic_record_count": len(automatic),
            "manual_duplicates_hidden": len(manual["records"]) - len(manual_rows),
            "feed_snapshot": feed.get("source")}


def summary(records):
    """Describe imported evidence, without inferring holdings or performance."""
    return {
        "total": len(records),
        "buys": sum(row["side"] == "buy" for row in records),
        "sells": sum(row["side"] == "sell" for row in records),
        "symbol_count": len({row["symbol"] for row in records}),
        "member_count": len({row["member"] for row in records}),
        "latest_available_date": max((row["available_date"] for row in records), default=None),
        "average_lag_days": round(sum(row["lag_days"] for row in records) / len(records), 2) if records else None,
    }


def browse(document, member="", symbol="", side="", query="", offset=0, limit=100):
    """Filter evidence pages while keeping whole-dataset summaries explicit."""
    records = document["records"]
    symbol = normalized_symbol(symbol) if symbol.strip() else ""
    query = query.strip().casefold()
    filtered = [row for row in reversed(records)
                if (not member or row["member"] == member)
                and (not symbol or row["symbol"] == symbol)
                and (not side or row["side"] == side)
                and (not query or any(query in row[column].casefold() for column in COLUMNS))]
    by_member = {}
    for row in records:
        by_member.setdefault(row["member"], []).append(row)
    automatic = bool(document.get("automatic_record_count"))
    collection = document.get("collection")
    return {
        "records": filtered[offset:offset + limit], "total": len(filtered), "offset": offset,
        "members": sorted(by_member), "symbols": sorted({row["symbol"] for row in records}),
        "last_import": document.get("last_import"), "mode": "automatic_and_csv" if automatic else "csv_import",
        "live_feed_connected": bool(collection and collection.get("enabled") and collection.get("last_success")),
        "collection": collection,
        "summary": summary(records), "filtered_summary": summary(filtered),
        "member_profiles": [{"member": name, **summary(by_member[name])} for name in sorted(by_member)],
        "provenance": {"source": "mixed_disclosures" if automatic else "user_supplied_csv", "dates_verified": False,
                       "manual_duplicates_hidden": document.get("manual_duplicates_hidden", 0),
                       "limitations": AUTOMATIC_LIMITATIONS if automatic else PROVENANCE_LIMITATIONS},
    }


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if reader.fieldnames != COLUMNS:
        raise ValueError("CSV headers must be: " + ",".join(COLUMNS))
    rows, keys = [], set()
    for number, row in enumerate(reader, 2):
        if number > 5001:
            raise ValueError("Import at most 5,000 disclosures at a time")
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Row {number}: incorrect number of columns")
        row = {k: v.strip() for k, v in row.items()}
        try:
            if any(not row[k] for k in COLUMNS):
                raise ValueError("Every column is required, including owner and asset type")
            if any(len(v) > 1000 for v in row.values()):
                raise ValueError("Field too long")
            if len(row["member"]) > 150:
                raise ValueError("Member must be at most 150 characters")
            transaction, available = date.fromisoformat(row["transaction_date"]), date.fromisoformat(row["available_date"])
            if transaction > available or available > market_today():
                raise ValueError("Dates must be ordered and cannot be in the future")
            row["transaction_date"], row["available_date"] = transaction.isoformat(), available.isoformat()
            row["symbol"] = normalized_symbol(row["symbol"])
            if row["side"] not in {"buy", "sell"}:
                raise ValueError("Side must be buy or sell")
            if row["asset_type"] not in {"stock", "etf", "option", "other"}:
                raise ValueError("Asset type must be stock, etf, option, or other")
            parsed = urlsplit(row["source_url"])
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Source must be an HTTPS evidence URL")
            # IDs are individual transaction rows, not a multi-row report's identifier.
            key = row["disclosure_id"]
            if key.startswith("cst:"):
                raise ValueError("The cst: ID prefix is reserved for automatically collected records")
            if key in keys:
                raise ValueError("Duplicate transaction disclosure_id within import")
            keys.add(key)
            row["lag_days"] = (available - transaction).days
            row["imported_at"] = datetime.now(timezone.utc).isoformat()
            row["content_hash"] = hashlib.sha256(repr(sorted((k, row[k]) for k in COLUMNS)).encode()).hexdigest()
            rows.append(row)
        except ValueError as exc:
            raise ValueError(f"Row {number}: {exc}") from exc
    if not rows:
        raise ValueError("CSV contains no disclosures")
    return rows


def merge_import(previous, rows):
    document = previous or {"id": "congress", "kind": "congress", "revision": 0, "records": []}
    existing = {row["disclosure_id"]: row for row in document["records"]}
    inserted, duplicates = 0, 0
    for row in rows:
        key = row["disclosure_id"]
        if key in existing:
            if existing[key]["content_hash"] != row["content_hash"]:
                raise ValueError(f"Conflicting disclosure {key}; amendments require a separate review and are not supported by this importer")
            duplicates += 1
        else:
            existing[key] = row
            inserted += 1
    if len(existing) > 10000:
        raise ValueError("This research workspace supports at most 10,000 disclosures")
    document["records"] = sorted(existing.values(), key=lambda r: (r["available_date"], r["transaction_date"], r["disclosure_id"]))
    document["revision"] += 1
    document["last_import"] = {"inserted": inserted, "duplicates": duplicates, "imported_at": datetime.now(timezone.utc).isoformat()}
    return document
