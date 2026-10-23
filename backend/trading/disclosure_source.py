"""Bounded, source-attributed Congress snapshots; never execute publisher code.

The publisher's availability timestamp estimates the end of the filing day in
New York. It is not an observed public-release time. Keep every event version so
the caller can distinguish current research from information known in the past.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import time
from collections import Counter
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import requests

PROVIDER = "congressional_stock_trades"
DATASET = "austin-starks/congressional-stock-trades"
SOURCE_URL = f"https://huggingface.co/datasets/{DATASET}"
LICENSE_URL = f"{SOURCE_URL}/blob/main/LICENSE_DATA.md"
API_URL = f"https://huggingface.co/api/datasets/{DATASET}"
NEW_YORK = ZoneInfo("America/New_York")
MAX_FILE_BYTES = 5_000_000
MAX_TOTAL_BYTES = 20_000_000
MAX_ROWS = 100_000
MAX_UNCOMPRESSED_BYTES = 100_000_000
MAX_FILES = 8
SCHEMA_COLUMNS = {
    "eventId", "version", "chamber", "owner", "action", "partialSale",
    "transactionDate", "ticker", "assetDescription", "assetTypeCode", "assetTypeLabel",
    "amountLow", "amountHigh", "firstAvailableAt", "availableAt", "supersededAt",
    "sourceDocId", "sourceRowIndex", "sourceUrl", "memberId", "displayName", "identitySource",
}


class DisclosureSourceError(ValueError):
    """The remote snapshot cannot safely replace the last verified snapshot."""


def _trusted_download_url(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    trusted = host == "huggingface.co" or host.endswith(".huggingface.co") or host.endswith(".hf.co")
    if (parsed.scheme != "https" or not trusted or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment):
        raise DisclosureSourceError("Disclosure download left the approved Hugging Face hosts")


def _download(url, maximum):
    """Manually validate redirects and bound both advertised and streamed sizes."""
    started = time.monotonic()
    for _ in range(4):
        remaining = 90 - (time.monotonic() - started)
        if remaining <= 0:
            raise DisclosureSourceError("Disclosure download exceeded its time limit")
        _trusted_download_url(url)
        try:
            with requests.get(url, stream=True, allow_redirects=False, timeout=(min(10, remaining), min(45, remaining)),
                              headers={"User-Agent": "StockScope/1.0 public-disclosure-research"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        raise DisclosureSourceError("Disclosure download returned an empty redirect")
                    url = urljoin(url, location)
                    continue
                if response.status_code != 200:
                    raise DisclosureSourceError(f"Disclosure source returned HTTP {response.status_code}")
                length = response.headers.get("Content-Length")
                if length and (not length.isdigit() or int(length) > maximum):
                    raise DisclosureSourceError("Disclosure download exceeds the size limit")
                chunks, size = [], 0
                for chunk in response.iter_content(chunk_size=65_536):
                    if time.monotonic() - started > 90:
                        raise DisclosureSourceError("Disclosure download exceeded its time limit")
                    size += len(chunk)
                    if size > maximum:
                        raise DisclosureSourceError("Disclosure download exceeds the size limit")
                    chunks.append(chunk)
                return b"".join(chunks)
        except requests.RequestException:
            # Requests exceptions can include signed CDN URLs; do not persist them.
            raise DisclosureSourceError("Disclosure source could not be reached") from None
    raise DisclosureSourceError("Disclosure download exceeded the redirect limit")


def _json(url, maximum):
    try:
        value = json.loads(_download(url, maximum))
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, DisclosureSourceError):
            raise
        raise DisclosureSourceError("Disclosure source returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise DisclosureSourceError("Disclosure source returned an invalid object")
    return value


def _instant(value, field, optional=False):
    if value is None and optional:
        return None
    try:
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, str):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise ValueError()
        # Parquet timestamp[us] values are UTC without timezone metadata.
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as exc:
        raise DisclosureSourceError(f"Disclosure source has an invalid {field}") from exc


def _iso(value):
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def _text(value, field, maximum=1000, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise DisclosureSourceError(f"Disclosure source has an invalid {field}")
    return value.strip()


def _official_url(value, chamber, doc_id):
    parsed = urlsplit(_text(value, "source URL"))
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.query or parsed.fragment:
        raise DisclosureSourceError("Disclosure evidence URL is not an approved official report")
    if chamber == "house":
        valid = parsed.hostname == "disclosures-clerk.house.gov" and re.fullmatch(
            rf"/public_disc/ptr-pdfs/20\d{{2}}/{re.escape(doc_id)}\.pdf", parsed.path)
    else:
        valid = parsed.hostname == "efdsearch.senate.gov" and re.fullmatch(
            rf"/search/view/(?:ptr|paper)/{re.escape(doc_id)}/", parsed.path, re.IGNORECASE)
    if not valid:
        raise DisclosureSourceError("Disclosure evidence URL does not match its official document")
    return value


def _asset_type(code, label, description):
    words = description.casefold()
    label = (label or "").casefold()
    if code == "OP" or "option" in label or re.search(r"\b(?:call|put)\s+options?\b|\boptions?\b", words):
        return "option"
    # Explicit non-equity codes win over descriptive words and ticker presence.
    if code and code not in {"ST", "EF", "OT"}:
        return "other"
    if label and label not in {"stock", "etf", "exchange traded fund", "other"}:
        return "other"
    if re.search(r"\b(?:non[- ]public|privately traded|private stock|restricted stock)\b", words):
        return "other"
    if code == "EF" or label == "etf" or re.search(r"\betf\b|\bexchange[- ]traded fund\b", words):
        return "etf"
    if code == "ST" or label == "stock" or re.search(r"\b(?:common|ordinary)\s+(?:stock|shares)\b", words):
        return "stock"
    return "other"


def _amount(low, high):
    for value in (low, high):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or not 0 <= value <= 1_000_000_000_000):
            raise DisclosureSourceError("Disclosure source has an invalid reported amount")
    if low is not None and high is not None and low > high:
        raise DisclosureSourceError("Disclosure source has a reversed reported amount range")
    def money(value):
        return f"${value:,.0f}" if value == int(value) else f"${value:,.2f}"
    if low is not None and high is not None:
        return f"{money(low)} - {money(high)}"
    if low is not None:
        return f"Over {money(low)}"
    if high is not None:
        return f"Up to {money(high)}"
    return "Not reported"


def normalize_record(raw, now):
    """Return (normalized version, None) or (None, auditable exclusion reason)."""
    chamber = raw.get("chamber")
    if chamber not in {"house", "senate"}:
        raise DisclosureSourceError("Disclosure source has an invalid chamber")
    event_id = _text(raw.get("eventId"), "event ID", 100)
    doc_id = _text(raw.get("sourceDocId"), "document ID", 36)
    id_pattern = r"\d{1,15}" if chamber == "house" else r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
    if not re.fullmatch(id_pattern, doc_id) or not re.fullmatch(rf"{chamber}:{id_pattern}:\d{{1,6}}", event_id):
        raise DisclosureSourceError("Disclosure source has an invalid document/event ID")
    version = raw.get("version")
    if type(version) is not int or not 1 <= version <= 100:
        raise DisclosureSourceError("Disclosure source has an invalid event version")
    source_row_index = raw.get("sourceRowIndex")
    if type(source_row_index) is not int or not 0 <= source_row_index <= MAX_ROWS:
        raise DisclosureSourceError("Disclosure source has an invalid source row index")
    source_url = _official_url(raw.get("sourceUrl"), chamber, doc_id)
    available = _instant(raw.get("availableAt"), "availability date")
    first_available = _instant(raw.get("firstAvailableAt"), "first availability date")
    superseded = _instant(raw.get("supersededAt"), "supersession date", optional=True)
    if first_available > available or (superseded is not None and superseded <= available):
        raise DisclosureSourceError("Disclosure event versions have inconsistent availability dates")
    today = now.astimezone(NEW_YORK).date()
    # Today's conservative end-of-day boundary can still be hours in the future.
    if available.astimezone(NEW_YORK).date() > today or (superseded is not None and superseded.astimezone(NEW_YORK).date() > today):
        raise DisclosureSourceError("Disclosure source contains future availability dates")
    available_day = available.astimezone(NEW_YORK).date()
    for value in (available, first_available, superseded):
        if value is not None:
            local = value.astimezone(NEW_YORK)
            if (local.hour, local.minute, local.second, local.microsecond) != (23, 59, 59, 999000):
                raise DisclosureSourceError("Disclosure availability no longer follows the documented filing-day estimate")
    transaction = raw.get("transactionDate")
    try:
        if isinstance(transaction, datetime):
            raise ValueError()
        transaction = transaction if isinstance(transaction, date) else date.fromisoformat(transaction)
    except (TypeError, ValueError):
        return None, "missing_or_invalid_transaction_date"
    if transaction > available_day or transaction.year < 2012:
        return None, "inconsistent_transaction_date"
    if raw.get("action") not in {"purchase", "sale"}:
        return None, "unsupported_action"
    ticker = raw.get("ticker")
    if ticker is None or ticker == "":
        return None, "missing_ticker"
    if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker.strip().upper()):
        return None, "unsupported_ticker"
    if raw.get("identitySource") not in {"legislators", "override"}:
        return None, "unresolved_member"
    member_id = _text(raw.get("memberId"), "member ID", 10)
    if not re.fullmatch(r"[A-Z]\d{6}", member_id):
        raise DisclosureSourceError("Disclosure source has an invalid member ID")
    owner = raw.get("owner")
    if owner not in {"self", "spouse", "dependent_child", "joint", "not_indicated"}:
        raise DisclosureSourceError("Disclosure source has an invalid owner")
    description = _text(raw.get("assetDescription"), "asset description", 2000)
    code = _text(raw.get("assetTypeCode"), "asset code", 10, optional=True)
    label = _text(raw.get("assetTypeLabel"), "asset label", 100, optional=True)
    partial_sale = raw.get("partialSale")
    if type(partial_sale) is not bool:
        raise DisclosureSourceError("Disclosure source has an invalid partial-sale marker")
    row = {
        "disclosure_id": f"cst:{event_id}:v{version}", "event_id": event_id, "version": version,
        "member": _text(raw.get("displayName"), "member name", 150), "member_id": member_id,
        "owner": owner, "symbol": ticker.strip().upper(), "side": "buy" if raw["action"] == "purchase" else "sell",
        "transaction_date": transaction.isoformat(), "available_date": available_day.isoformat(),
        "asset_type": _asset_type(code, label, description),
        "amount_range": _amount(raw.get("amountLow"), raw.get("amountHigh")), "source_url": source_url,
        "lag_days": (available_day - transaction).days, "source": PROVIDER, "chamber": chamber,
        "source_doc_id": doc_id, "source_row_index": source_row_index, "filed_date": available_day.isoformat(),
        "availability_basis": "filing_day_estimate", "provider_available_at": _iso(available),
        "first_available_at": _iso(first_available), "superseded_at": _iso(superseded),
        "is_amendment": version > 1, "asset_description": description,
        "source_asset_type_code": code, "source_asset_type_label": label,
        "partial_sale": partial_sale,
        "source_comment": _text(raw.get("comment"), "source comment", 65536, optional=True),
    }
    # A future amendment legitimately closes this version's information window.
    content = {key: value for key, value in row.items() if key != "superseded_at"}
    row["content_hash"] = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return row, None


def _read_parquet(data):
    import pyarrow.parquet as pq
    try:
        parquet = pq.ParquetFile(io.BytesIO(data))
        metadata = parquet.metadata
        if (metadata.num_rows > MAX_ROWS or metadata.num_columns > 64 or metadata.num_row_groups > 128
                or sum(metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups)) > MAX_UNCOMPRESSED_BYTES):
            raise DisclosureSourceError("Disclosure shard exceeds the decoded-size limit")
        if not SCHEMA_COLUMNS.issubset(set(parquet.schema_arrow.names)):
            raise DisclosureSourceError("Disclosure shard is missing required schema columns")
        # No dataset discovery, filesystem extensions or remote reads by Arrow.
        return parquet.read(use_threads=False).to_pylist()
    except DisclosureSourceError:
        raise
    except Exception as exc:
        raise DisclosureSourceError("Disclosure shard is not valid Parquet") from exc


def fetch_snapshot(previous=None, now=None):
    """Fetch recent years and continue validating previously collected history.

    ``previous`` is prior metadata, not the whole feed. An unchanged revision
    returns no rows, so the caller must preserve its previously stored records.
    """
    started = time.monotonic()
    def check_budget():
        if time.monotonic() - started > 240:
            raise DisclosureSourceError("Disclosure snapshot exceeded its total time limit")
    now = _instant(now or datetime.now(timezone.utc), "current time")
    info = _json(API_URL, 256_000)
    revision = info.get("sha")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise DisclosureSourceError("Disclosure dataset revision is invalid")
    year = now.astimezone(NEW_YORK).year
    retained_years = previous.get("years", []) if previous else []
    if (not isinstance(retained_years, list)
            or any(type(value) is not int or not 2012 <= value <= year for value in retained_years)):
        raise DisclosureSourceError("Prior disclosure snapshot has invalid coverage years")
    # Retained history must not become permanently unchecked at New Year.
    # Existing file/row limits bound growth; reaching them requires review.
    wanted_years = sorted({year - 1, year, *retained_years})
    required_years = {year - 1, *retained_years}
    if previous and previous.get("revision") == revision and previous.get("requested_years") == wanted_years:
        return {"records": [], "metadata": dict(previous), "unchanged": True}
    base = f"{SOURCE_URL}/resolve/{revision}/"
    manifest = _json(base + "snapshot.json", 512_000)
    check_budget()
    audit = manifest.get("audit")
    if (manifest.get("schemaVersion") != 2 or manifest.get("dataset") != DATASET
            or not isinstance(audit, dict) or audit.get("passed") is not True):
        raise DisclosureSourceError("Disclosure snapshot schema or publisher audit is not valid")
    generated = _instant(manifest.get("generatedAt"), "snapshot generation time")
    source_checked = _instant(manifest.get("lastSourceCheckAt"), "source check time")
    if generated > now or source_checked > now or source_checked > generated:
        raise DisclosureSourceError("Disclosure snapshot has inconsistent freshness timestamps")
    tables = manifest.get("tables")
    if not isinstance(tables, dict) or not isinstance(tables.get("political_trade_events"), dict):
        raise DisclosureSourceError("Disclosure snapshot has no event table")
    table = tables["political_trade_events"]
    shards = table.get("manifests")
    if not isinstance(shards, list):
        raise DisclosureSourceError("Disclosure snapshot has no event manifests")
    selected = [item for item in shards if isinstance(item, dict) and item.get("year") in wanted_years]
    years = sorted(item["year"] for item in selected)
    if len(years) != len(set(years)) or not required_years.issubset(years):
        raise DisclosureSourceError("Disclosure snapshot is missing the requested history")
    files, paths, total_size = [], set(), 0
    for shard in selected:
        shard_files = shard.get("files")
        if not isinstance(shard_files, list) or not shard_files:
            raise DisclosureSourceError("Disclosure snapshot has no shard files")
        for entry in shard_files:
            if not isinstance(entry, dict):
                raise DisclosureSourceError("Disclosure snapshot has an invalid shard entry")
            path, digest, size = entry.get("publicPath"), entry.get("sha256"), entry.get("size")
            pattern = rf"data/political_trade_events/{shard['year']}-\d{{5}}-of-\d{{5}}\.parquet"
            if not isinstance(path, str) or not re.fullmatch(pattern, path) or path in paths:
                raise DisclosureSourceError("Disclosure snapshot has an invalid or duplicate shard path")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise DisclosureSourceError("Disclosure snapshot has an invalid shard checksum")
            if type(size) is not int or not 0 < size <= MAX_FILE_BYTES:
                raise DisclosureSourceError("Disclosure snapshot has an invalid shard size")
            files.append({"path": path, "sha256": digest, "size": size})
            paths.add(path)
            total_size += size
    if len(files) > MAX_FILES or total_size > MAX_TOTAL_BYTES:
        raise DisclosureSourceError("Disclosure snapshot exceeds the download budget")
    records, seen, excluded, samples = [], set(), Counter(), []
    source_rows = 0
    for file in files:
        check_budget()
        data = _download(base + file["path"], file["size"])
        if len(data) != file["size"] or hashlib.sha256(data).hexdigest() != file["sha256"]:
            raise DisclosureSourceError("Disclosure shard failed its size or SHA-256 check")
        raw_rows = _read_parquet(data)
        source_rows += len(raw_rows)
        if source_rows > MAX_ROWS:
            raise DisclosureSourceError("Disclosure snapshot exceeds the row budget")
        for raw in raw_rows:
            row, reason = normalize_record(raw, now)
            if reason:
                excluded[reason] += 1
                if len(samples) < 20:
                    samples.append({"event_id": raw.get("eventId"), "source_url": raw.get("sourceUrl"), "reason": reason})
                continue
            if row["disclosure_id"] in seen:
                raise DisclosureSourceError("Disclosure snapshot repeats an event version")
            seen.add(row["disclosure_id"])
            records.append(row)
    if not records:
        raise DisclosureSourceError("Disclosure snapshot contains no usable transactions")
    check_budget()
    records.sort(key=lambda row: (row["available_date"], row["transaction_date"], row["disclosure_id"]))
    days = [row["available_date"] for row in records]
    totals = manifest.get("totals", {})
    if (not isinstance(totals, dict) or any(type(totals.get(key)) is not int or not 0 <= totals[key] <= 10_000_000
                                          for key in ("events", "filings", "failedFilings"))):
        raise DisclosureSourceError("Disclosure snapshot has invalid coverage counts")
    metadata = {
        "provider": PROVIDER, "source_url": SOURCE_URL, "license_url": LICENSE_URL,
        "revision": revision, "source_checked_at": _iso(source_checked), "generated_at": _iso(generated),
        "years": years, "requested_years": wanted_years,
        "source_counts": {"selected_event_versions": source_rows, "accepted_event_versions": len(records),
                          "snapshot_event_versions": totals.get("events"), "snapshot_filings": totals.get("filings"),
                          "snapshot_failed_filings": totals.get("failedFilings")},
        "excluded_counts": dict(excluded), "excluded_samples": samples,
        "coverage_start": min(days), "coverage_end": max(days), "files": files,
        "availability_basis": "filing_day_estimate", "publisher_target_interval_hours": 20,
    }
    return {"records": records, "metadata": metadata, "unchanged": False}
