"""Normalize saved evidence without inventing dates, scores, or predictions."""

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from backend.core.atomic_file import atomic_text_writer

SNAPSHOT_TYPES = {
    "sec_sentiment": "sec", "sec_filings": "sec",
    "news_sentiment": "news", "comprehensive_news": "news",
    "sec_companyfacts": "financial_facts",
}


def repository():
    """A configured database is authoritative; failures never fall back to disk."""
    from backend.db import get_repository
    return get_repository()


def data_directory() -> Path:
    return Path(os.getenv("STOCKSCOPE_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def normalized_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
        raise ValueError("Invalid stock symbol format")
    return symbol


def save_records(symbol: str, suffix: str, records: list) -> str:
    """Save a versioned database snapshot, or an atomic file in local file mode."""
    repo = repository()
    if repo is not None:
        return repo.save_snapshot(symbol, suffix, records)
    directory = data_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{normalized_symbol(symbol)}_{suffix}.json"
    with atomic_text_writer(path) as handle:
        json.dump(records, handle, indent=2, allow_nan=False)
    return str(path)


def saved_snapshots(symbol: str, suffixes=None, *, strict=False):
    symbol = normalized_symbol(symbol)
    selected = set(SNAPSHOT_TYPES) if suffixes is None else set(suffixes)
    if not selected.issubset(SNAPSHOT_TYPES):
        raise ValueError("Unsupported research snapshot suffix")
    repo = repository()
    if repo is not None:
        return repo.load_snapshots(symbol, selected)
    snapshots = []
    for path in sorted(data_directory().glob(f"{symbol}_*.json")):
        suffix = path.name[len(symbol) + 1:-5].lower()
        if suffix not in selected:
            continue
        try:
            records = json.loads(path.read_text())
        except (OSError, ValueError):
            if strict:
                raise
            continue
        if strict and not isinstance(records, list):
            raise ValueError("Invalid saved research snapshot")
        if isinstance(records, list):
            snapshots.append((suffix, records))
    return snapshots


def list_saved_symbols():
    repo = repository()
    if repo is not None:
        return repo.list_symbols()
    symbols = set()
    for path in data_directory().glob("*_*.json"):
        symbol, suffix = path.stem.split("_", 1)
        if suffix not in SNAPSHOT_TYPES:
            continue
        try:
            symbols.add(normalized_symbol(symbol))
        except ValueError:
            continue
    return sorted(symbols)


def delete_saved_research(symbol: str):
    symbol = normalized_symbol(symbol)
    repo = repository()
    if repo is not None:
        return repo.delete_symbol_research(symbol)
    removed = []
    for path in data_directory().glob(f"{symbol}_*.json"):
        path.unlink()
        removed.append(path.name)
    return removed


def read_records_reference(reference):
    if not reference:
        return []
    if isinstance(reference, dict):
        reference = reference.get("reference")
        if not reference:
            return []
    if str(reference).startswith("db://"):
        repo = repository()
        if repo is None:
            raise RuntimeError("A database is required to read this snapshot")
        return repo.read_snapshot_reference(reference)
    payload = json.loads(Path(reference).read_text())
    return payload if isinstance(payload, list) else []


def _is_social_record(record):
    return record.get("source_type") in {"social", "social_post"} or any(
        str(record.get(field, "")).strip().lower() in {"stocktwits", "reddit", "twitter"}
        for field in ("source", "provider")
    )


def saved_news(symbol: str, limit: int = 20, *, strict=False):
    articles, seen = [], set()
    for suffix, records in saved_snapshots(symbol, ("news_sentiment", "comprehensive_news"), strict=strict):
        if SNAPSHOT_TYPES.get(suffix) != "news":
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            if _is_social_record(record):
                continue
            identity = record.get("url") or record.get("title")
            if not identity or identity in seen:
                continue
            seen.add(identity)
            articles.append(record)
    articles.sort(key=lambda item: parse_timestamp(item.get("publishedAt")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return articles[:limit]


def query_saved_news(symbol: str, *, limit=20, offset=0, sort="date-desc", exclude_sources=()):
    """Filter and order the entire deduplicated saved collection before slicing."""
    if sort not in {"date-desc", "date-asc", "sentiment-desc", "sentiment-asc"}:
        raise ValueError("Unsupported saved-news order")
    articles = saved_news(symbol, None, strict=True)
    source = lambda row: row.get("source") or "Unknown Source"
    sources = sorted({source(row) for row in articles})
    excluded = set(exclude_sources)
    matches = [row for row in articles if source(row) not in excluded]

    def value(row):
        if sort.startswith("date"):
            stamp = parse_timestamp(row.get("publishedAt"))
            return stamp.timestamp() if stamp else None
        tone = row.get("sentiment")
        score = tone.get("compound") if isinstance(tone, dict) else None
        if row.get("source_type") == "company_release" or isinstance(score, bool):
            return None
        return score if isinstance(score, (int, float)) and math.isfinite(score) and -1 <= score <= 1 else None

    def ordering(row):
        observation = value(row)
        # URL/title is the existing deduplication identity; it breaks ties in
        # both directions. Unknown dates and unavailable tone always sort last.
        identity = str(row.get("url") or row.get("title"))
        return (observation is None, -(observation or 0) if sort.endswith("desc") else (observation or 0), identity)

    matches.sort(key=ordering)
    total = len(matches)
    offset = min(offset, ((total - 1) // limit) * limit) if total else 0
    page = matches[offset:offset + limit]
    return {"ticker": symbol, "articles": page, "count": len(page),
            "total": total, "saved_total": len(articles), "sources": sources,
            "offset": offset, "limit": limit, "has_more": offset + len(page) < total}


def saved_sec_facts(symbol: str):
    for suffix, records in saved_snapshots(symbol, ("sec_companyfacts",)):
        if suffix == "sec_companyfacts" and records and isinstance(records[0], dict):
            return records[0]
    return None


def parse_timestamp(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        result = pd.to_datetime(value, unit="s", utc=True) if isinstance(value, (int, float)) else pd.to_datetime(value, utc=True)
        return None if pd.isna(result) else result.to_pydatetime()
    except (ValueError, TypeError, OverflowError):
        return None


def load_evidence(symbol: str) -> pd.DataFrame:
    symbol = normalized_symbol(symbol)
    records, seen = [], set()
    for suffix, data in saved_snapshots(symbol, ("sec_sentiment", "sec_filings", "news_sentiment", "comprehensive_news")):
        source_type = SNAPSHOT_TYPES.get(suffix)
        if source_type not in {"sec", "news"}:
            continue
        if not isinstance(data, list):
            continue
        for original in data:
            if not isinstance(original, dict):
                continue
            item = dict(original)
            if source_type == "sec":
                # Both legacy event snapshots and the primary SEC API contract.
                item["accession_number"] = item.get("accession_number") or item.get("accession")
                item["form_type"] = item.get("form_type") or item.get("form")
                item["filing_date"] = item.get("filing_date") or item.get("filed")
                item["url"] = item.get("url") or item.get("filing_url")
            identity = (source_type, item.get("url") or item.get("accession_number") or item.get("title"))
            if identity[1] and identity in seen:
                continue
            seen.add(identity)
            item["source_type"] = source_type
            if source_type == "news" and original.get("source_type") in {"company_release", "social", "social_post"}:
                item["source_type"] = "social" if original["source_type"] in {"social", "social_post"} else "company_release"
            item["source"] = "SEC" if source_type == "sec" else str(item.get("source") or source_type.title())
            if source_type == "news" and _is_social_record(original):
                item["source_type"] = "social"
            # Preserve the provider's original value before creating the normalized column.
            item["original_created_utc"] = item.get("created_utc")
            timestamp = None
            for field in ("created_utc", "created", "publishedAt", "timestamp", "filing_date"):
                timestamp = parse_timestamp(item.get(field))
                if timestamp is not None:
                    break
            item["created_utc"] = timestamp
            score = original.get("compound")
            if isinstance(original.get("sentiment"), dict):
                score = original["sentiment"].get("compound")
            try:
                score = float(score)
                if not math.isfinite(score) or not -1 <= score <= 1:
                    score = None
            except (ValueError, TypeError):
                score = None
            if item["source_type"] in {"sec", "company_release"}:
                # Old snapshots scored boilerplate by filing type. Never reuse those scores.
                score = None
                item.pop("sentiment", None)
                item.pop("sentiment_context", None)
            item["compound"] = score
            records.append(item)
    frame = pd.DataFrame(records)
    if not frame.empty:
        frame["created_utc"] = pd.to_datetime(frame["created_utc"], utc=True, errors="coerce")
        frame["compound"] = pd.to_numeric(frame["compound"], errors="coerce")
    return frame


def latest_timestamp(frame):
    if frame.empty or "created_utc" not in frame:
        return None
    dates = pd.to_datetime(frame["created_utc"], utc=True, errors="coerce").dropna()
    return dates.max().to_pydatetime() if len(dates) else None


def freshness(as_of, now=None):
    if as_of is None:
        return "unknown"
    age = (now or datetime.now(timezone.utc)) - as_of
    if age.total_seconds() < -300:
        return "unknown"
    return "recent" if age.total_seconds() <= 7 * 86400 else "stale"


def sentiment_metrics(frame):
    scores = pd.Series(dtype=float)
    if not frame.empty and "compound" in frame:
        eligible = frame[frame["source_type"] == "news"] if "source_type" in frame else frame[frame["source"] == "News"]
        scores = pd.to_numeric(eligible["compound"], errors="coerce").dropna()
        scores = scores[scores.between(-1, 1)]
    average = float(scores.mean()) if len(scores) else None
    positive, negative = int((scores >= .05).sum()), int((scores <= -.05).sum())
    return {
        "avg_sentiment": average,
        "sentiment_distribution": {"positive": positive, "negative": negative, "neutral": len(scores) - positive - negative},
        "trend": "unavailable" if average is None else "positive" if average >= .05 else "negative" if average <= -.05 else "neutral",
        "sample_size": len(scores),
        "method": "VADER text tone of saved news items; not a return forecast. SEC filings, company releases, and social posts excluded.",
    }


def source_analyses(frame):
    sources = []
    if frame.empty:
        return sources
    for source, group in frame.groupby("source", sort=True):
        as_of = latest_timestamp(group)
        sources.append({"source": source, "count": len(group), "avg_sentiment": sentiment_metrics(group)["avg_sentiment"], "latest_update": as_of, "freshness": evidence_freshness(group), "unknown_timestamps": int(group["created_utc"].isna().sum())})
    return sources


def evidence_freshness(frame):
    """A new item must not conceal missing dates or old items in the same sample."""
    if frame.empty or frame["created_utc"].isna().any():
        return "unknown"
    states = {freshness(value.to_pydatetime()) for value in frame["created_utc"]}
    return "unknown" if "unknown" in states else "stale" if "stale" in states else "recent"


def filing_events(frame):
    if frame.empty:
        return []
    events = []
    for row in frame[frame["source_type"] == "sec"].to_dict("records"):
        filed = parse_timestamp(row.get("filing_date"))
        events.append({"form_type": str(row.get("form_type") or "Unknown"), "filing_date": filed.date().isoformat() if filed else None, "url": row.get("url") if isinstance(row.get("url"), str) else "", "description": str(row.get("description") or "SEC filing")})
    return sorted(events, key=lambda event: event["filing_date"] or "", reverse=True)
