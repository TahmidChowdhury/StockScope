"""Bounded, explicitly requested SEC evidence collection; no derived financial metrics.

SEC companyfacts includes standard, entity-wide XBRL concepts, not every custom
concept or segment. A fiscal period/frame is filing context, not proof that a
duration is one discrete quarter. Preserve the original periods and filings.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from collections import OrderedDict
from datetime import date, datetime, timezone
from typing import Any

import requests

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_CACHE_BYTES = 32 * 1024 * 1024
MAX_CACHE_ENTRIES = 8
REQUEST_TIMEOUT = (3.0, 10.0)
REQUEST_DEADLINE_SECONDS = 30.0
REQUEST_INTERVAL_SECONDS = 0.5  # At most two requests/sec in this process.
_CACHE: OrderedDict = OrderedDict()
_FETCH_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configured_user_agent(user_agent: str | None = None) -> str | None:
    """Require a declared contact; never manufacture a working contact address."""
    value = (user_agent if user_agent is not None else os.getenv("SEC_USER_AGENT", "")).strip()
    if not value or len(value) > 256 or "\n" in value or "\r" in value:
        return None
    match = re.search(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value)
    if not match:
        return None
    email = match.group().lower()
    local, domain = email.rsplit("@", 1)
    if (domain in {"example.com", "example.org", "example.net", "stockscope.app"}
            or domain.endswith((".example", ".invalid", ".test"))
            or local in {"your-email", "youremail", "your_email", "your.name", "your-name"}):
        return None
    return value


def is_sec_configured(user_agent: str | None = None) -> bool:
    return configured_user_agent(user_agent) is not None


def _configured_concepts() -> set[tuple[str, str]] | None:
    """Optional storage control, e.g. ``us-gaap:Revenues,us-gaap:Assets``.

    Selection never drops units, dates, or amendments within a selected concept.
    An unset allowlist means all standard concepts supplied by companyfacts.
    """
    configured = os.getenv("SEC_FACT_CONCEPTS", "").strip()
    if not configured:
        return None
    entries = {entry.strip() for entry in configured.split(",") if entry.strip()}
    if not entries or len(entries) > 100 or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*:[A-Za-z][A-Za-z0-9_.-]*", entry) for entry in entries):
        raise ValueError("SEC_FACT_CONCEPTS must be up to 100 comma-separated taxonomy:concept identifiers")
    return {tuple(entry.split(":", 1)) for entry in entries}


def _cik(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    text = str(value).strip() if value is not None else ""
    return text.zfill(10) if re.fullmatch(r"\d{1,10}", text) and int(text) > 0 else None


def _symbol(value: str) -> str:
    result = value.strip().upper().replace(".", "-")
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{0,9}", result):
        raise ValueError("Invalid stock symbol format")
    return result


def _iso_date(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _json_safe(value: Any) -> Any:
    # Public JSON rejects nonfinite numbers. Keep invalid input legible in raw data.
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _identity(value: Any) -> str:
    return hashlib.sha256(json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _filing_url(cik: str, accession: Any) -> str | None:
    if not isinstance(accession, str) or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{accession}-index.html"


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite JSON number")
    return number


def _invalid_constant(value: str):
    raise ValueError("Invalid JSON constant")


def _request_json(url: str, user_agent: str, ttl: int = 900) -> dict:
    """Cache successful responses and failures; never retry a rate-limit response.

    Rate limiting is process-local. Deployments sharing one SEC contact must also
    keep their combined request rate below the SEC's published limit.
    """
    global _LAST_REQUEST_AT
    if not (url == TICKERS_URL or re.fullmatch(r"https://data\.sec\.gov/(?:api/xbrl/companyfacts|submissions)/CIK\d{10}\.json", url)):
        raise ValueError("Unapproved SEC endpoint")
    with _FETCH_LOCK:
        current = time.monotonic()
        cached = _CACHE.get(url)
        if cached and cached["expires_at"] > current:
            _CACHE.move_to_end(url)
            return {**cached["result"], "from_cache": True}
        wait = REQUEST_INTERVAL_SECONDS - (current - _LAST_REQUEST_AT)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST_AT = time.monotonic()
        result = {"status": "failed", "url": url, "retrieved_at": None, "from_cache": False, "error": None, "data": None}
        cache_seconds, size = 60, 0
        try:
            with requests.get(url, headers={"User-Agent": user_agent, "Accept": "application/json"},
                              timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=False) as response:
                result["http_status"] = response.status_code
                if response.status_code != 200:
                    result["error"] = f"http_{response.status_code}"
                    retry_after = response.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        cache_seconds = max(60, min(int(retry_after), 3600))
                else:
                    declared = response.headers.get("Content-Length", "")
                    if declared.isdigit() and int(declared) > MAX_RESPONSE_BYTES:
                        raise ValueError("response_too_large")
                    chunks = []
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if time.monotonic() - _LAST_REQUEST_AT > REQUEST_DEADLINE_SECONDS:
                            raise TimeoutError("request_deadline")
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise ValueError("response_too_large")
                        chunks.append(chunk)
                    data = json.loads(b"".join(chunks).decode("utf-8"), parse_float=_finite_float, parse_constant=_invalid_constant)
                    if not isinstance(data, dict):
                        raise ValueError("invalid_json_shape")
                    result.update(status="completed", retrieved_at=_now(), data=data)
                    cache_seconds = ttl
        except (requests.RequestException, TimeoutError):
            result["error"] = "request_failed_or_timed_out"
        except (ValueError, UnicodeError, RecursionError) as error:
            result["error"] = str(error) if str(error) in {"response_too_large", "invalid_json_shape"} else "invalid_json"
        _CACHE[url] = {"expires_at": time.monotonic() + cache_seconds, "result": result, "size": size if result["data"] else 0}
        _CACHE.move_to_end(url)
        while len(_CACHE) > MAX_CACHE_ENTRIES or sum(entry["size"] for entry in _CACHE.values()) > MAX_CACHE_BYTES:
            _CACHE.popitem(last=False)
        return result


def normalize_companyfacts(payload: dict, cik: str, *, concepts: set[tuple[str, str]] | None = None) -> list[dict]:
    """Preserve every reported fact version, including units and amendments."""
    cik = _cik(cik)
    if cik is None or _cik(payload.get("cik")) != cik:
        raise ValueError("Companyfacts CIK does not match requested company")
    groups = payload.get("facts")
    if not isinstance(groups, dict):
        raise ValueError("Companyfacts facts object is missing")
    source_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    rows, seen = [], set()
    for taxonomy, definitions in groups.items():
        if not isinstance(definitions, dict):
            continue
        for concept, definition in definitions.items():
            if concepts is not None and (taxonomy, concept) not in concepts:
                continue
            if not isinstance(definition, dict) or not isinstance(definition.get("units"), dict):
                continue
            for unit, observations in definition["units"].items():
                if not isinstance(observations, list):
                    continue
                for raw in observations:
                    if not isinstance(raw, dict):
                        continue
                    fact_id = _identity([cik, taxonomy, concept, unit, raw])
                    if fact_id in seen:  # Only byte-equivalent contextual duplicates.
                        continue
                    seen.add(fact_id)
                    start, end, filed = (_iso_date(raw.get(key)) for key in ("start", "end", "filed"))
                    issues = []
                    for key, parsed in (("end", end), ("filed", filed)):
                        if parsed is None:
                            issues.append(f"missing_or_invalid_{key}")
                    if raw.get("start") is not None and start is None:
                        issues.append("invalid_start")
                    duration = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 if start and end else None
                    if duration is not None and duration <= 0:
                        issues.append("end_before_start")
                        duration = None
                    period_kind = "duration" if duration is not None else "instant" if end and "start" not in raw else "unknown"
                    value = raw.get("val")
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)):
                        value = None
                        issues.append("missing_or_invalid_value")
                    accession = raw.get("accn") if isinstance(raw.get("accn"), str) else None
                    if not _filing_url(cik, accession):
                        issues.append("missing_or_invalid_accession")
                    fiscal_year = raw.get("fy")
                    if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
                        fiscal_year = None
                    rows.append({"fact_id": fact_id, "cik": cik, "taxonomy": taxonomy, "concept": concept,
                                 "label": definition.get("label"), "unit": unit, "value": value,
                                 "start": start, "end": end, "filed": filed, "accession": accession,
                                 "form": raw.get("form"), "fiscal_year": fiscal_year, "fiscal_period": raw.get("fp"),
                                 "frame": raw.get("frame"), "period_kind": period_kind, "duration_days": duration,
                                 "validation_issues": issues, "source_url": source_url,
                                 "filing_url": _filing_url(cik, accession), "raw_fact": _json_safe(raw)})
    return sorted(rows, key=lambda row: (row["taxonomy"], row["concept"], row["unit"], row["end"] or "", row["filed"] or "", row["fact_id"]))


def normalize_submissions(payload: dict, cik: str) -> list[dict]:
    """Normalize the recent submissions table; do not imply full filing history."""
    cik = _cik(cik)
    if cik is None or _cik(payload.get("cik")) != cik:
        raise ValueError("Submissions CIK does not match requested company")
    recent = payload.get("filings", {}).get("recent") if isinstance(payload.get("filings"), dict) else None
    if not isinstance(recent, dict) or not isinstance(recent.get("accessionNumber"), list):
        raise ValueError("Submissions recent table is missing")
    source_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    rows = []
    for index, accession in enumerate(recent["accessionNumber"]):
        raw = {key: values[index] if index < len(values) else None for key, values in recent.items() if isinstance(values, list)}
        filed, report_date = _iso_date(raw.get("filingDate")), _iso_date(raw.get("reportDate"))
        issues = [] if filed else ["missing_or_invalid_filed"]
        if not _filing_url(cik, accession):
            issues.append("missing_or_invalid_accession")
        rows.append({"filing_id": _identity([cik, raw]), "cik": cik, "accession": accession,
                     "form": raw.get("form"), "filed": filed, "report_date": report_date,
                     "acceptance_datetime": raw.get("acceptanceDateTime"), "primary_document": raw.get("primaryDocument"),
                     "items": raw.get("items"), "is_xbrl": raw.get("isXBRL"), "is_inline_xbrl": raw.get("isInlineXBRL"),
                     "source_url": source_url, "filing_url": _filing_url(cik, accession),
                     "validation_issues": issues, "raw_filing": _json_safe(raw)})
    return rows


def select_facts_for_period(facts: list[dict], *, taxonomy: str, concept: str, unit: str,
                          start: str | None, end: str, filed_on_or_before: str | None = None) -> list[dict]:
    """Exact period/unit selection retaining all versions, not an accounting engine.

    A filing-date cutoff filters reported dates only. It is not a guarantee of
    point-in-time availability, and records with unknown filing dates are excluded.
    """
    if not _iso_date(end) or (start is not None and not _iso_date(start)):
        raise ValueError("Explicit valid period dates are required")
    if start and start > end:
        raise ValueError("Period start must not be after its end")
    if filed_on_or_before is not None and not _iso_date(filed_on_or_before):
        raise ValueError("Invalid filing-date cutoff")
    return [row for row in facts if row.get("taxonomy") == taxonomy and row.get("concept") == concept
            and row.get("unit") == unit and row.get("start") == start and row.get("end") == end
            and row.get("period_kind") == ("instant" if start is None else "duration")
            and (filed_on_or_before is None or (row.get("filed") is not None and row["filed"] <= filed_on_or_before))]


def _collection_metadata(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "data"}


def collect_sec_facts(symbol: str, *, user_agent: str | None = None, cik: str | int | None = None) -> dict:
    """Fetch an evidence snapshot only when explicitly called and configured.

    At most three SEC requests: ticker map (if needed), companyfacts, submissions.
    Persist this entire envelope as ``sec_companyfacts``; persistence owns first_seen.
    """
    symbol = _symbol(symbol)
    snapshot = {"symbol": symbol, "cik": None, "entity_name": None, "status": "not_configured", "facts": [], "filings": [],
                "metadata": {"collected_at": _now(), "retrieved_at": None, "as_of": None,
                             "as_of_basis": "latest_reported_filing_date", "latest_filed": None,
                             "facts_latest_filed": None, "filings_latest_filed": None,
                             "companyfacts_url": None, "submissions_url": None, "collections": {},
                             "limitations": ["Standard entity-wide XBRL concepts only; custom concepts and segment disclosures may be absent.",
                                             "Units and exact periods remain separate; no quarterly or trailing-twelve-month metrics are synthesized.",
                                             "All reported fact versions are retained; fiscal periods and frames do not establish a discrete quarter.",
                                             "Filing dates do not establish historical public availability or a point-in-time backtest dataset.",
                                             "Submissions cover the SEC recent table only; older referenced files are not fetched."]}}
    metadata = snapshot["metadata"]
    agent = configured_user_agent(user_agent)
    if agent is None:
        metadata["configuration_error"] = "Set SEC_USER_AGENT to an organization/application name and an actual monitored contact email."
        return snapshot
    try:
        concepts = _configured_concepts()
    except ValueError as error:
        snapshot["status"] = "failed"
        metadata["configuration_error"] = str(error)
        return snapshot
    metadata["concept_filter"] = sorted(f"{taxonomy}:{concept}" for taxonomy, concept in concepts) if concepts is not None else None
    metadata["max_response_bytes"] = MAX_RESPONSE_BYTES
    company_cik = _cik(cik)
    if cik is not None and company_cik is None:
        raise ValueError("CIK must contain one to ten digits")
    if company_cik is None:
        mapping = _request_json(TICKERS_URL, agent, ttl=86400)
        metadata["collections"]["ticker_mapping"] = _collection_metadata(mapping)
        if mapping["status"] != "completed":
            snapshot["status"] = "failed"
            return snapshot
        for item in mapping["data"].values():
            if isinstance(item, dict) and str(item.get("ticker", "")).upper().replace(".", "-") == symbol:
                company_cik = _cik(item.get("cik_str"))
                if company_cik:
                    break
        if company_cik is None:
            snapshot["status"] = "not_found"
            return snapshot
    snapshot["cik"] = company_cik
    metadata["companyfacts_url"] = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company_cik}.json"
    metadata["submissions_url"] = f"https://data.sec.gov/submissions/CIK{company_cik}.json"
    retrieved = []
    for collection, output, normalizer in (("companyfacts", "facts", normalize_companyfacts), ("submissions", "filings", normalize_submissions)):
        response = _request_json(metadata[f"{collection}_url"], agent)
        collection_meta = _collection_metadata(response)
        if response["status"] == "completed":
            try:
                snapshot[output] = (normalizer(response["data"], company_cik, concepts=concepts)
                                    if collection == "companyfacts" else normalizer(response["data"], company_cik))
                snapshot["entity_name"] = snapshot["entity_name"] or response["data"].get("entityName") or response["data"].get("name")
                collection_meta["record_count"] = len(snapshot[output])
                if response.get("retrieved_at"):
                    retrieved.append(response["retrieved_at"])
                if collection == "submissions":
                    metadata["older_submissions_files"] = response["data"].get("filings", {}).get("files", [])
            except ValueError:
                collection_meta.update(status="failed", error="invalid_or_mismatched_company_payload")
        metadata["collections"][collection] = collection_meta
    statuses = [metadata["collections"][name]["status"] for name in ("companyfacts", "submissions")]
    snapshot["status"] = "completed" if all(status == "completed" for status in statuses) else "partial" if "completed" in statuses else "failed"
    metadata["retrieved_at"] = min(retrieved) if retrieved else None  # Oldest component, not the newest cached fetch.
    metadata["facts_latest_filed"] = max((row["filed"] for row in snapshot["facts"] if row["filed"]), default=None)
    metadata["filings_latest_filed"] = max((row["filed"] for row in snapshot["filings"] if row["filed"]), default=None)
    metadata["latest_filed"] = max((value for value in (metadata["facts_latest_filed"], metadata["filings_latest_filed"]) if value), default=None)
    metadata["as_of"] = metadata["latest_filed"]
    metadata["fact_count"] = len(snapshot["facts"])
    metadata["filing_count"] = len(snapshot["filings"])
    # Compact encoding estimate excludes this size field; database/index overhead
    # and indented filesystem snapshots require additional storage.
    metadata["snapshot_compact_bytes_estimate"] = len(json.dumps(snapshot, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    return snapshot
