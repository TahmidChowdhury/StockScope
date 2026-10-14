"""Offline SEC contract tests: periods, revisions, provenance, and bounded I/O."""

import copy
import json

import pytest

from backend.services import sec_facts as sec

CIK = "0000320193"
AGENT = "StockScope Research sec-research@investor-domain.com"
FACT_URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"


@pytest.fixture(autouse=True)
def isolated_concept_config(monkeypatch):
    monkeypatch.delenv("SEC_FACT_CONCEPTS", raising=False)


def observation(**changes):
    return {"start": "2025-01-01", "end": "2025-03-31", "val": 100,
            "accn": "0000320193-25-000001", "fy": 2025, "fp": "Q1", "form": "10-Q",
            "filed": "2025-05-01", "frame": "CY2025Q1", **changes}


def companyfacts(*observations, units=None):
    return {"cik": 320193, "entityName": "Test Issuer",
            "facts": {"us-gaap": {"Revenues": {"label": "Revenue", "description": "Reported revenue",
                                                "units": units if units is not None else {"USD": list(observations)}}}}}


def submissions():
    return {"cik": CIK, "name": "Test Issuer", "filings": {
        "recent": {"accessionNumber": ["0000320193-25-000001", "0000320193-25-000002"],
                   "form": ["10-Q", "10-Q/A"], "filingDate": ["2025-05-01", "2025-05-20"],
                   "reportDate": ["2025-03-31", "2025-03-31"],
                   "acceptanceDateTime": ["2025-05-01T16:01:00.000Z", "2025-05-20T15:00:00.000Z"],
                   "primaryDocument": ["quarterly.htm", "amendment.htm"], "isXBRL": [1, 1]},
        "files": [{"name": "CIK0000320193-submissions-001.json", "filingCount": 2000}]}}


def fetched(data=None, status="completed", **changes):
    return {"status": status, "data": data, "retrieved_at": "2026-10-14T12:00:00+00:00" if data else None,
            "url": FACT_URL, "from_cache": False, "error": None if status == "completed" else "http_429", **changes}


def test_amendments_and_repeat_filings_are_distinct_evidence():
    original = observation()
    amended = observation(val=110, accn="0000320193-25-000002", form="10-Q/A", filed="2025-05-20")
    repeated = observation(accn="0000320193-26-000001", filed="2026-05-01", fy=2026)
    rows = sec.normalize_companyfacts(companyfacts(original, amended, repeated, original), CIK)
    assert len(rows) == 3
    assert len({row["fact_id"] for row in rows}) == 3
    assert {row["value"] for row in rows} == {100, 110}
    assert [row["raw_fact"] for row in rows] == [original, amended, repeated]
    assert all(row["duration_days"] == 90 and row["period_kind"] == "duration" for row in rows)
    assert rows[0]["source_url"] == FACT_URL
    assert rows[0]["filing_url"].endswith("/000032019325000001/0000320193-25-000001-index.html")
    reversed_rows = sec.normalize_companyfacts(companyfacts(repeated, amended, original), CIK)
    assert rows == reversed_rows


def test_units_taxonomies_and_concepts_never_collide():
    payload = companyfacts(units={"USD": [observation()], "CAD": [observation()], "shares": [observation()]})
    payload["facts"]["ifrs-full"] = copy.deepcopy(payload["facts"]["us-gaap"])
    payload["facts"]["us-gaap"]["Assets"] = copy.deepcopy(payload["facts"]["us-gaap"]["Revenues"])
    rows = sec.normalize_companyfacts(payload, CIK)
    assert len(rows) == len({row["fact_id"] for row in rows}) == 9
    selected = sec.select_facts_for_period(rows, taxonomy="us-gaap", concept="Revenues", unit="USD", start="2025-01-01", end="2025-03-31")
    assert len(selected) == 1


def test_exact_duration_selection_does_not_mistake_q2_ytd_for_quarter():
    rows = sec.normalize_companyfacts(companyfacts(
        observation(start="2025-01-01", end="2025-06-30", fp="Q2", val=250),
        observation(start="2025-04-01", end="2025-06-30", fp="Q2", val=150)), CIK)
    selected = sec.select_facts_for_period(rows, taxonomy="us-gaap", concept="Revenues", unit="USD", start="2025-04-01", end="2025-06-30")
    assert [row["value"] for row in selected] == [150]
    assert {row["duration_days"] for row in rows} == {91, 181}
    assert not sec.select_facts_for_period(rows, taxonomy="us-gaap", concept="Revenues", unit="USD", start="2025-07-01", end="2025-09-30")


def test_unknown_filing_dates_are_not_invented_and_cutoff_excludes_them():
    rows = sec.normalize_companyfacts(companyfacts(observation(filed=None), observation(), observation(filed="2025-05-20", form="10-Q/A")), CIK)
    selected = sec.select_facts_for_period(rows, taxonomy="us-gaap", concept="Revenues", unit="USD", start="2025-01-01", end="2025-03-31", filed_on_or_before="2025-05-10")
    assert len(selected) == 1 and selected[0]["filed"] == "2025-05-01"
    missing = next(row for row in rows if row["filed"] is None)
    assert missing["raw_fact"]["filed"] is None
    assert "missing_or_invalid_filed" in missing["validation_issues"]
    assert "first_seen" not in missing and "data_first_seen" not in missing


@pytest.mark.parametrize("changes,kind,issue", [
    ({"end": None}, "unknown", "missing_or_invalid_end"),
    ({"end": "2025-02-30"}, "unknown", "missing_or_invalid_end"),
    ({"start": "2025-04-01"}, "unknown", "end_before_start"),
    ({"start": "bad"}, "unknown", "invalid_start"),
    ({"val": float("inf")}, "duration", "missing_or_invalid_value"),
    ({"val": True}, "duration", "missing_or_invalid_value"),
])
def test_invalid_values_and_periods_remain_visible(changes, kind, issue):
    row = sec.normalize_companyfacts(companyfacts(observation(**changes)), CIK)[0]
    assert row["period_kind"] == kind and issue in row["validation_issues"]
    json.dumps(row, allow_nan=False)


def test_instant_facts_and_zero_values_are_preserved():
    raw = observation(val=0)
    raw.pop("start")
    row = sec.normalize_companyfacts(companyfacts(raw), CIK)[0]
    assert row["value"] == 0 and row["period_kind"] == "instant" and row["duration_days"] is None
    assert sec.select_facts_for_period([row], taxonomy="us-gaap", concept="Revenues", unit="USD", start=None, end="2025-03-31") == [row]


def test_submissions_amendments_and_short_columns_preserve_provenance():
    payload = submissions()
    payload["filings"]["recent"]["filingDate"] = ["2025-05-01"]
    rows = sec.normalize_submissions(payload, CIK)
    assert len(rows) == 2 and rows[1]["form"] == "10-Q/A"
    assert rows[1]["filed"] is None and rows[1]["raw_filing"]["filingDate"] is None
    assert rows[0]["acceptance_datetime"] == "2025-05-01T16:01:00.000Z"
    assert rows[0]["filing_id"] != rows[1]["filing_id"]


@pytest.mark.parametrize("agent", ["", "StockScope research tool", "StockScope test@example.com", "StockScope your-email@domain.com", "StockScope contact@stockscope.app", "StockScope real@domain.com\nInjected: value"])
def test_unconfigured_or_placeholder_contacts_do_not_request(monkeypatch, agent):
    monkeypatch.setattr(sec, "_request_json", lambda *args, **kwargs: pytest.fail("No SEC request permitted"))
    result = sec.collect_sec_facts("AAPL", user_agent=agent)
    assert result["status"] == "not_configured" and result["metadata"]["retrieved_at"] is None


def test_collection_uses_optional_cik_and_reports_actual_coverage(monkeypatch):
    calls = []
    def fetch(url, agent, ttl=900):
        calls.append(url)
        return fetched(companyfacts(observation())) if "companyfacts" in url else fetched(submissions(), retrieved_at="2026-10-14T12:01:00+00:00")
    monkeypatch.setattr(sec, "_request_json", fetch)
    result = sec.collect_sec_facts("aapl", user_agent=AGENT, cik=320193)
    assert len(calls) == 2 and result["cik"] == CIK and result["status"] == "completed"
    meta = result["metadata"]
    assert meta["retrieved_at"] == "2026-10-14T12:00:00+00:00"
    assert meta["as_of"] == "2025-05-20" and meta["facts_latest_filed"] == "2025-05-01"
    assert meta["older_submissions_files"][0]["filingCount"] == 2000
    assert meta["collections"]["companyfacts"]["record_count"] == 1
    json.dumps(result, allow_nan=False)


def test_mapping_normalizes_share_class_symbols_and_not_found(monkeypatch):
    calls = []
    def fetch(url, agent, ttl=900):
        calls.append((url, ttl))
        if url == sec.TICKERS_URL:
            return fetched({"0": {"ticker": "BRK-B", "cik_str": 320193}})
        return fetched(companyfacts()) if "companyfacts" in url else fetched(submissions())
    monkeypatch.setattr(sec, "_request_json", fetch)
    result = sec.collect_sec_facts("BRK.B", user_agent=AGENT)
    assert result["symbol"] == "BRK-B" and result["cik"] == CIK
    assert calls[0] == (sec.TICKERS_URL, 86400) and len(calls) == 3
    calls.clear()
    assert sec.collect_sec_facts("MISSING", user_agent=AGENT)["status"] == "not_found"
    assert len(calls) == 1


def test_partial_collection_keeps_successful_facts(monkeypatch):
    monkeypatch.setattr(sec, "_request_json", lambda url, agent: fetched(companyfacts(observation())) if "companyfacts" in url else fetched(status="failed"))
    result = sec.collect_sec_facts("AAPL", user_agent=AGENT, cik=CIK)
    assert result["status"] == "partial" and len(result["facts"]) == 1 and not result["filings"]
    assert result["metadata"]["collections"]["submissions"]["error"] == "http_429"


def test_wrong_issuer_is_rejected_without_losing_other_collection(monkeypatch):
    wrong = companyfacts(observation())
    wrong["cik"] = 42
    monkeypatch.setattr(sec, "_request_json", lambda url, agent: fetched(wrong) if "companyfacts" in url else fetched(submissions()))
    result = sec.collect_sec_facts("AAPL", user_agent=AGENT, cik=CIK)
    assert result["status"] == "partial" and result["facts"] == [] and len(result["filings"]) == 2
    assert result["metadata"]["collections"]["companyfacts"]["error"] == "invalid_or_mismatched_company_payload"


class Response:
    def __init__(self, data=b'{}', status=200, headers=None):
        self.data, self.status_code, self.headers = data, status, headers or {}
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def iter_content(self, chunk_size):
        yield self.data


@pytest.fixture
def clean_cache(monkeypatch):
    monkeypatch.setattr(sec, "_CACHE", sec.OrderedDict())
    monkeypatch.setattr(sec, "REQUEST_INTERVAL_SECONDS", 0)


def test_transport_has_timeout_size_limit_and_cache_preserves_retrieval(monkeypatch, clean_cache):
    calls = []
    response = Response(b'{"cik": 320193}')
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return response
    monkeypatch.setattr(sec.requests, "get", get)
    first = sec._request_json(FACT_URL, AGENT)
    second = sec._request_json(FACT_URL, AGENT)
    assert first["status"] == "completed" and not first["from_cache"] and second["from_cache"]
    assert first["retrieved_at"] == second["retrieved_at"] and len(calls) == 1
    assert calls[0][1] == {"headers": {"User-Agent": AGENT, "Accept": "application/json"}, "timeout": (3.0, 10.0), "stream": True, "allow_redirects": False}
    assert response.closed


@pytest.mark.parametrize("response,error", [
    (Response(b'123456', headers={"Content-Length": "6"}), "response_too_large"),
    (Response(b'123456'), "response_too_large"),
    (Response(b'NaN'), "invalid_json"),
    (Response(b'[]'), "invalid_json_shape"),
    (Response(b'{}', status=429, headers={"Retry-After": "120"}), "http_429"),
    (Response(b'{}', status=302, headers={"Location": "https://untrusted.invalid"}), "http_302"),
])
def test_failures_are_bounded_cached_and_not_retried(monkeypatch, clean_cache, response, error):
    monkeypatch.setattr(sec, "MAX_RESPONSE_BYTES", 5)
    calls = []
    monkeypatch.setattr(sec.requests, "get", lambda *args, **kwargs: (calls.append(1), response)[1])
    first = sec._request_json(FACT_URL, AGENT)
    second = sec._request_json(FACT_URL, AGENT)
    assert first["error"] == error and first["status"] == "failed"
    assert first["retrieved_at"] is None and second["from_cache"] and len(calls) == 1 and response.closed


def test_unapproved_urls_and_invalid_ciks_are_rejected(monkeypatch):
    monkeypatch.setattr(sec.requests, "get", lambda *args, **kwargs: pytest.fail("No request permitted"))
    with pytest.raises(ValueError):
        sec._request_json("https://example.org/", AGENT)
    with pytest.raises(ValueError):
        sec.collect_sec_facts("AAPL", user_agent=AGENT, cik="../123")


def test_no_date_cutoff_or_period_guess_is_accepted():
    with pytest.raises(ValueError):
        sec.select_facts_for_period([], taxonomy="us-gaap", concept="Revenues", unit="USD", start="Q1", end="2025-03-31")
    with pytest.raises(ValueError):
        sec.select_facts_for_period([], taxonomy="us-gaap", concept="Revenues", unit="USD", start=None, end="2025-03-31", filed_on_or_before="yesterday")


def test_configured_concept_filter_preserves_units_and_amendments(monkeypatch):
    payload = companyfacts(units={"USD": [observation(), observation(val=110, form="10-Q/A")], "CAD": [observation()]})
    payload["facts"]["us-gaap"]["Assets"] = copy.deepcopy(payload["facts"]["us-gaap"]["Revenues"])
    monkeypatch.setenv("SEC_FACT_CONCEPTS", "us-gaap:Revenues")
    monkeypatch.setattr(sec, "_request_json", lambda url, agent: fetched(payload) if "companyfacts" in url else fetched(submissions()))
    result = sec.collect_sec_facts("AAPL", user_agent=AGENT, cik=CIK)
    assert len(result["facts"]) == 3 and {row["concept"] for row in result["facts"]} == {"Revenues"}
    assert {row["unit"] for row in result["facts"]} == {"USD", "CAD"}
    assert result["metadata"]["concept_filter"] == ["us-gaap:Revenues"]
    assert result["metadata"]["snapshot_compact_bytes_estimate"] > 1000


def test_invalid_concept_filter_stops_before_network(monkeypatch):
    monkeypatch.setenv("SEC_FACT_CONCEPTS", "just guess some revenue")
    monkeypatch.setattr(sec, "_request_json", lambda *args, **kwargs: pytest.fail("Invalid configuration must not call SEC"))
    result = sec.collect_sec_facts("AAPL", user_agent=AGENT)
    assert result["status"] == "failed" and "SEC_FACT_CONCEPTS" in result["metadata"]["configuration_error"]
