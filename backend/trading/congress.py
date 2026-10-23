"""Disclosure imports retain dates and provenance; no inferred original trade prices."""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from backend.services.research import normalized_symbol
from backend.trading.market import market_today

COLUMNS = ["disclosure_id", "member", "owner", "symbol", "side", "transaction_date", "available_date", "asset_type", "amount_range", "source_url"]


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
