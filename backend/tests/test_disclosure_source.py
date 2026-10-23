"""Source boundaries, evidence dates and amendments using offline Parquet."""
import hashlib
import io
import json
from datetime import date, datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from backend.trading import disclosure_source as source

NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)
REVISION = "a" * 40


def event(year=2026, **changes):
    return {
        "eventId": f"house:{year}0001:0", "version": 1, "chamber": "house",
        "owner": "spouse", "action": "purchase", "partialSale": False,
        "transactionDate": date(year, 1, 2), "ticker": "AAPL", "assetDescription": "Apple Inc. Common Stock",
        "assetTypeCode": "ST", "assetTypeLabel": None, "amountLow": 1001.0, "amountHigh": 15000.0,
        "firstAvailableAt": datetime(year, 1, 7, 4, 59, 59, 999000),
        "availableAt": datetime(year, 1, 7, 4, 59, 59, 999000), "supersededAt": None,
        "sourceDocId": f"{year}0001", "sourceRowIndex": 0,
        "sourceUrl": f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{year}0001.pdf",
        "memberId": "A000379", "displayName": "Mark Alford", "identitySource": "legislators", "comment": None,
        **changes,
    }


def wire_snapshot(monkeypatch, by_year=None):
    by_year = by_year or {2025: [event(2025)], 2026: [event()]}
    downloads, manifests = {}, []
    base = f"{source.SOURCE_URL}/resolve/{REVISION}/"
    for year, rows in by_year.items():
        buffer = io.BytesIO()
        pq.write_table(pa.Table.from_pylist(rows), buffer)
        data = buffer.getvalue()
        path = f"data/political_trade_events/{year}-00000-of-00001.parquet"
        downloads[base + path] = data
        manifests.append({"year": year, "files": [{"publicPath": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}]})
    manifest = {
        "schemaVersion": 2, "dataset": source.DATASET, "generatedAt": "2026-10-22T17:23:00Z",
        "lastSourceCheckAt": "2026-10-22T17:23:00Z", "audit": {"passed": True},
        "tables": {"political_trade_events": {"manifests": manifests}},
        "totals": {"events": 2, "filings": 2, "failedFilings": 0},
    }
    def download(url, maximum):
        if url == source.API_URL:
            return json.dumps({"sha": REVISION}).encode()
        if url == base + "snapshot.json":
            return json.dumps(manifest).encode()
        return downloads[url]
    monkeypatch.setattr(source, "_download", download)
    return downloads, manifest


def test_pinned_checksummed_snapshot_retains_versions_and_exclusions(monkeypatch):
    original = event(supersededAt=datetime(2026, 2, 7, 4, 59, 59, 999000))
    amendment = event(version=2, amountHigh=50000, availableAt=datetime(2026, 2, 7, 4, 59, 59, 999000))
    wire_snapshot(monkeypatch, {2025: [event(2025)], 2026: [original, amendment,
                    event(eventId="house:20260001:1", ticker=None),
                    event(eventId="house:20260001:2", action="exchange")]})
    snapshot = source.fetch_snapshot(now=NOW)
    assert not snapshot["unchanged"]
    assert len(snapshot["records"]) == 3
    old, amended = [row for row in snapshot["records"] if row["event_id"] == original["eventId"]]
    assert old["version"] == 1 and amended["version"] == 2
    assert old["superseded_at"] == amended["provider_available_at"]
    assert amended["is_amendment"]
    assert old["available_date"] == "2026-01-06"  # UTC is Jan 7; filing day is Jan 6 in New York.
    assert old["lag_days"] == 4
    assert old["amount_range"] == "$1,001 - $15,000"
    assert snapshot["metadata"]["excluded_counts"] == {"missing_ticker": 1, "unsupported_action": 1}
    assert len(snapshot["metadata"]["excluded_samples"]) == 2
    assert snapshot["metadata"]["source_counts"]["selected_event_versions"] == 5
    assert "observed_at" not in old and "first_seen_at" not in old


def test_summer_availability_is_end_of_new_york_filing_day():
    row, reason = source.normalize_record(event(
        transactionDate=date(2026, 7, 1), firstAvailableAt=datetime(2026, 7, 8, 3, 59, 59, 999000),
        availableAt=datetime(2026, 7, 8, 3, 59, 59, 999000)), NOW)
    assert reason is None
    assert row["available_date"] == row["filed_date"] == "2026-07-07"
    assert row["availability_basis"] == "filing_day_estimate"


def test_todays_filing_can_have_a_conservative_boundary_later_today():
    noon = datetime(2026, 1, 6, 17, tzinfo=timezone.utc)
    row, reason = source.normalize_record(event(), noon)
    assert reason is None and row["filed_date"] == "2026-01-06"


def test_supersession_can_close_window_without_changing_economic_hash():
    first, _ = source.normalize_record(event(), NOW)
    superseded, _ = source.normalize_record(event(supersededAt=datetime(2026, 7, 8, 3, 59, 59, 999000)), NOW)
    changed, _ = source.normalize_record(event(amountHigh=50000), NOW)
    assert first["content_hash"] == superseded["content_hash"]
    assert first["content_hash"] != changed["content_hash"]


@pytest.mark.parametrize("changes,expected", [
    ({"assetTypeCode": "OP", "assetDescription": "SPY ETF call options"}, "option"),
    ({"assetTypeCode": "EF", "assetDescription": "Index fund"}, "etf"),
    ({"assetTypeCode": None, "assetTypeLabel": "Stock", "assetDescription": "iShares CMBS ETF"}, "etf"),
    ({"assetTypeCode": "PS", "assetDescription": "Private Common Stock"}, "other"),
    ({"assetTypeCode": None, "assetTypeLabel": "Non-Public Stock", "assetDescription": "Example ordinary shares"}, "other"),
    ({"assetTypeCode": None, "assetTypeLabel": "Corporate Bond", "assetDescription": "Shares linked corporate debt"}, "other"),
    ({"assetTypeCode": None, "assetTypeLabel": None, "assetDescription": "Unclassified asset"}, "other"),
    ({"assetTypeCode": None, "assetDescription": "Example ordinary shares"}, "stock"),
])
def test_asset_classification_never_infers_equity_from_ticker(changes, expected):
    row, _ = source.normalize_record(event(**changes), NOW)
    assert row["asset_type"] == expected


@pytest.mark.parametrize("changes", [
    {"sourceUrl": "https://example.com/20260001.pdf"},
    {"sourceUrl": "https://disclosures-clerk.house.gov.evil.test/public_disc/ptr-pdfs/2026/20260001.pdf"},
    {"sourceUrl": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/99999999.pdf"},
    {"sourceUrl": "https://user@disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20260001.pdf"},
    {"eventId": "house:../../20260001:0"}, {"version": True}, {"sourceRowIndex": -1},
    {"amountLow": float("nan")}, {"amountLow": 20000, "amountHigh": 15000},
    {"availableAt": datetime(2027, 1, 1)}, {"supersededAt": datetime(2025, 1, 1)},
    {"availableAt": datetime(2026, 1, 8, 16)},
])
def test_invalid_source_record_fails_closed(changes):
    with pytest.raises(source.DisclosureSourceError):
        source.normalize_record(event(**changes), NOW)


@pytest.mark.parametrize("changes,reason", [
    ({"ticker": None}, "missing_ticker"), ({"ticker": "ABC/DE"}, "unsupported_ticker"),
    ({"transactionDate": None}, "missing_or_invalid_transaction_date"),
    ({"transactionDate": date(2026, 2, 1)}, "inconsistent_transaction_date"),
    ({"action": "exchange"}, "unsupported_action"),
])
def test_unusable_source_rows_have_explicit_exclusion_reasons(changes, reason):
    assert source.normalize_record(event(**changes), NOW) == (None, reason)


def test_unchanged_revision_does_not_download_shards_but_new_year_changes_scope(monkeypatch):
    calls = []
    def download(url, maximum):
        calls.append(url)
        return json.dumps({"sha": REVISION}).encode()
    monkeypatch.setattr(source, "_download", download)
    previous = {"revision": REVISION, "requested_years": [2025, 2026]}
    result = source.fetch_snapshot(previous, NOW)
    assert result == {"records": [], "metadata": previous, "unchanged": True}
    assert calls == [source.API_URL]
    with pytest.raises(source.DisclosureSourceError):
        source.fetch_snapshot(previous, datetime(2027, 1, 2, tzinfo=timezone.utc))
    assert len(calls) == 3  # Revision alone cannot skip a new year's scope.


def test_year_rollover_continues_revalidating_all_collected_years(monkeypatch):
    wire_snapshot(monkeypatch, {2025: [event(2025)], 2026: [event(2026)], 2027: [event(2027)]})
    previous = {"revision": "b" * 40, "years": [2025, 2026], "requested_years": [2025, 2026]}
    result = source.fetch_snapshot(previous, datetime(2027, 10, 23, tzinfo=timezone.utc))
    assert result["metadata"]["years"] == [2025, 2026, 2027]
    assert result["metadata"]["requested_years"] == [2025, 2026, 2027]
    assert len(result["records"]) == 3
    assert any("/2025-" in file["path"] for file in result["metadata"]["files"])


def test_previously_collected_year_cannot_silently_disappear_at_rollover(monkeypatch):
    wire_snapshot(monkeypatch, {2026: [event(2026)], 2027: [event(2027)]})
    previous = {"revision": "b" * 40, "years": [2025, 2026], "requested_years": [2025, 2026]}
    with pytest.raises(source.DisclosureSourceError, match="missing the requested history"):
        source.fetch_snapshot(previous, datetime(2027, 10, 23, tzinfo=timezone.utc))


def test_new_calendar_year_can_wait_for_first_published_year_shard(monkeypatch):
    wire_snapshot(monkeypatch)
    previous = {"revision": "b" * 40, "years": [2025, 2026], "requested_years": [2025, 2026]}
    result = source.fetch_snapshot(previous, datetime(2027, 1, 2, tzinfo=timezone.utc))
    assert result["metadata"]["years"] == [2025, 2026]
    assert result["metadata"]["requested_years"] == [2025, 2026, 2027]


def test_checksum_mismatch_preserves_callers_last_good_snapshot(monkeypatch):
    downloads, _ = wire_snapshot(monkeypatch)
    path = next(iter(downloads))
    downloads[path] = b"x" * len(downloads[path])
    with pytest.raises(source.DisclosureSourceError, match="SHA-256"):
        source.fetch_snapshot(now=NOW)


@pytest.mark.parametrize("mutation", [
    lambda m: m.update(schemaVersion=3),
    lambda m: m["audit"].update(passed=False),
    lambda m: m.update(lastSourceCheckAt="2027-01-01T00:00:00Z"),
    lambda m: m["tables"]["political_trade_events"]["manifests"][0]["files"][0].update(publicPath="../../secrets"),
    lambda m: m["tables"]["political_trade_events"]["manifests"][0]["files"][0].update(size=source.MAX_FILE_BYTES + 1),
])
def test_invalid_manifest_cannot_promote_snapshot(monkeypatch, mutation):
    _, manifest = wire_snapshot(monkeypatch)
    mutation(manifest)
    with pytest.raises(source.DisclosureSourceError):
        source.fetch_snapshot(now=NOW)


def test_duplicate_event_versions_are_rejected(monkeypatch):
    wire_snapshot(monkeypatch, {2025: [event(2025)], 2026: [event(), event()]})
    with pytest.raises(source.DisclosureSourceError, match="repeats"):
        source.fetch_snapshot(now=NOW)


class Response:
    def __init__(self, status=200, headers=None, chunks=None):
        self.status_code, self.headers, self.chunks = status, headers or {}, chunks or []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def iter_content(self, chunk_size):
        return iter(self.chunks)


def test_redirect_to_untrusted_host_is_rejected_before_network_request(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        assert kwargs["allow_redirects"] is False
        return Response(302, {"Location": "http://127.0.0.1/private"})
    monkeypatch.setattr(source.requests, "get", get)
    with pytest.raises(source.DisclosureSourceError, match="approved"):
        source._download(source.API_URL, 100)
    assert calls == [source.API_URL]


def test_unadvertised_oversized_body_is_bounded(monkeypatch):
    monkeypatch.setattr(source.requests, "get", lambda *_args, **_kwargs: Response(chunks=[b"123", b"456"]))
    with pytest.raises(source.DisclosureSourceError, match="size limit"):
        source._download(source.API_URL, 5)


def test_missing_parquet_schema_is_rejected():
    buffer = io.BytesIO()
    pq.write_table(pa.table({"unexpected": [1]}), buffer)
    with pytest.raises(source.DisclosureSourceError, match="schema"):
        source._read_parquet(buffer.getvalue())
