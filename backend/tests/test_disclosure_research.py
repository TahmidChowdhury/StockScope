"""Offline disclosure research, observation-time signals and refresh permissions."""
import copy
import csv
import io
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.core.auth import create_access_token
from backend.routers.trading import router
from backend.services import research
from backend.trading import congress, disclosure_collector, disclosure_source, market, storage
from backend.trading.models import BacktestInput


@pytest.fixture
def context(monkeypatch, tmp_path):
    # All writes are isolated temporary files. Never connect to configured Postgres.
    monkeypatch.setenv("SECRET_KEY", "disclosure-research-offline-signing-key-123456789")
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path / "research"))
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "false")
    monkeypatch.setattr(research, "repository", lambda: None)
    monkeypatch.setattr(market, "market_today", lambda: date(2026, 10, 23))
    def no_source_fetch(*_args, **_kwargs):
        raise AssertionError("Integration tests must not fetch remote disclosures")
    monkeypatch.setattr(disclosure_source, "fetch_snapshot", no_source_fetch)
    def prices(symbols, start, end):
        rows, day = [], start
        while day <= end:
            if day.weekday() < 5:
                rows.append({"date": day.isoformat(), "open": 100.0, "close": 101.0, "split": 1.0, "dividend": 0.0})
            day += timedelta(days=1)
        return {symbol: copy.deepcopy(rows) for symbol in set(symbols)}
    monkeypatch.setattr(market, "fetch_bars", prices)
    app = FastAPI()
    app.include_router(router, prefix="/api/trading")
    headers = {role: {"Authorization": "Bearer " + create_access_token("fixture", role)}
               for role in ("admin", "guest", "demo")}
    with TestClient(app) as client:
        yield client, headers, monkeypatch


def automatic(**changes):
    return {
        "disclosure_id": "cst:house:20000001:0:v1", "event_id": "house:20000001:0", "version": 1,
        "member": "Example Member", "member_id": "A000379", "owner": "spouse", "symbol": "AAPL",
        "side": "buy", "transaction_date": "2025-01-02", "available_date": "2025-01-06",
        "asset_type": "stock", "amount_range": "$1,001 - $15,000", "lag_days": 4,
        "source_url": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20000001.pdf",
        "source": "congressional_stock_trades", "chamber": "house", "source_doc_id": "20000001",
        "filed_date": "2025-01-06", "availability_basis": "filing_day_estimate",
        "provider_available_at": "2025-01-07T04:59:59.999000Z", "superseded_at": None,
        "is_amendment": False, "asset_description": "Apple Common Stock",
        "first_seen_at": "2026-10-22T17:30:00+00:00", "content_hash": "fixture-original",
        **changes,
    }


def seed(rows, manual=None, collection=None):
    source = {"provider": "congressional_stock_trades", "revision": "a" * 40,
              "source_checked_at": "2026-10-22T17:23:00Z", "years": [2025, 2026],
              "availability_basis": "filing_day_estimate", "files": [{"path": "fixture.parquet", "sha256": "b" * 64, "size": 123}]}
    storage.mutate("congress-feed", lambda _: {"id": "congress-feed", "kind": "congress_feed", "revision": 1,
                   "records": rows, "source": source, "collection": collection or {"state": "completed", "last_success": "2026-10-22T17:30:00Z"}})
    if manual is not None:
        storage.mutate("congress", lambda _: {"id": "congress", "kind": "congress", "revision": 1, "records": manual})
    return source


def backtest(**changes):
    return {"strategy": "congress", "member": "Example Member", "start": "2025-01-01", "end": "2025-01-10", **changes}


def test_backfilled_record_cannot_create_a_historical_signal_by_default(context):
    client, headers, _ = context
    seed([automatic()])
    response = client.post("/api/trading/backtests", headers=headers["admin"], json=backtest())
    assert response.status_code == 422
    assert "first-observed" in response.json()["detail"]
    assert storage.listing("run") == []


def test_observed_signals_use_new_york_date_and_execute_next_session(context):
    client, headers, _ = context
    seed([automatic(first_seen_at="2025-01-09T02:30:00Z")])  # January 8 in New York.
    response = client.post("/api/trading/backtests", headers=headers["admin"], json=backtest())
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["allow_estimated_disclosure_dates"] is False
    assert len(run["result"]["fills"]) == 1
    fill = run["result"]["fills"][0]
    assert fill["signal_date"] == "2025-01-08"
    assert fill["execution_date"] == "2025-01-09"
    assert fill["availability_basis"] == "stockscope_first_observed"
    assert run["disclosures"][0]["signal_available_date"] == "2025-01-08"


def test_explicit_exploratory_history_preserves_its_assumptions_and_source_snapshot(context):
    client, headers, _ = context
    snapshot = seed([automatic()])
    response = client.post("/api/trading/backtests", headers=headers["admin"],
                           json=backtest(allow_estimated_disclosure_dates=True))
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["allow_estimated_disclosure_dates"] is True
    assert run["result"]["fills"][0]["execution_date"] == "2025-01-07"
    assert run["result"]["fills"][0]["availability_basis"] == "filing_day_estimate"
    assert run["disclosures"][0]["signal_availability_basis"] == "filing_day_estimate"
    assert any("look-ahead bias" in assumption for assumption in run["result"]["assumptions"])
    saved = client.get(f"/api/trading/backtests/{run['id']}/export", headers=headers["guest"]).json()
    assert saved["disclosure_snapshot"] == snapshot
    assert saved["disclosures"][0]["first_seen_at"] == "2026-10-22T17:30:00+00:00"
    assert saved["disclosures"][0]["provider_available_at"] == "2025-01-07T04:59:59.999000Z"
    assert saved["data"]["AAPL"]


def test_congress_accepts_empty_hidden_symbols_and_resolves_disclosure_symbols(context):
    client, headers, _ = context
    request = BacktestInput(**backtest(symbols=[], fast_window=50, slow_window=20,
                                     allow_estimated_disclosure_dates=True))
    assert request.symbols == []  # SMA-only settings must not constrain Congress inputs.
    seed([automatic()])
    response = client.post("/api/trading/backtests", headers=headers["admin"], json=request.model_dump(mode="json"))
    assert response.status_code == 201, response.text
    assert response.json()["resolved_symbols"] == ["AAPL"]
    assert response.json()["result"]["fills"][0]["symbol"] == "AAPL"


@pytest.mark.parametrize("strategy", ["buy_hold", "sma"])
def test_non_congress_strategies_still_require_a_symbol(context, strategy):
    with pytest.raises(ValidationError, match="at least one stock symbol"):
        BacktestInput(**backtest(strategy=strategy, symbols=[]))


def test_sma_window_order_remains_required_only_for_sma(context):
    with pytest.raises(ValidationError, match="Fast window must be shorter"):
        BacktestInput(**backtest(strategy="sma", symbols=["AAPL"], fast_window=50, slow_window=20))
    hold = BacktestInput(**backtest(strategy="buy_hold", symbols=["AAPL"], fast_window=50, slow_window=20))
    assert hold.strategy == "buy_hold"


def test_browse_uses_latest_versions_but_backtest_only_copies_original_once(context):
    client, headers, _ = context
    original = automatic(superseded_at="2025-02-07T04:59:59.999000Z")
    revised = automatic(disclosure_id="cst:house:20000001:0:v2", version=2, symbol="MSFT",
                        is_amendment=True, available_date="2025-02-06", content_hash="fixture-amended")
    orphan_amendment = automatic(disclosure_id="cst:house:20000002:0:v2", event_id="house:20000002:0",
                                version=2, is_amendment=True, symbol="NVDA")
    seed([original, revised, orphan_amendment])
    before = storage.read("congress-feed")
    browsed = client.get("/api/trading/congress", headers=headers["guest"]).json()
    assert {row["symbol"] for row in browsed["records"]} == {"MSFT", "NVDA"}
    assert browsed["total"] == 2
    response = client.post("/api/trading/backtests", headers=headers["admin"],
                           json=backtest(allow_estimated_disclosure_dates=True))
    assert response.status_code == 201, response.text
    run = response.json()
    assert [row["disclosure_id"] for row in run["disclosures"]] == [original["disclosure_id"]]
    assert [fill["symbol"] for fill in run["result"]["fills"]] == ["AAPL"]
    assert storage.read("congress-feed") == before


def test_original_marked_as_amendment_is_excluded(context):
    client, headers, _ = context
    seed([automatic(is_amendment=True)])
    response = client.post("/api/trading/backtests", headers=headers["admin"],
                           json=backtest(allow_estimated_disclosure_dates=True))
    assert response.status_code == 422
    assert storage.listing("run") == []


def test_default_mode_does_not_copy_a_version_superseded_before_first_observation(context):
    client, headers, _ = context
    original = automatic(first_seen_at="2025-01-08T12:00:00Z", superseded_at="2025-01-08T04:59:59.999Z")
    revised = automatic(disclosure_id="cst:house:20000001:0:v2", version=2, symbol="MSFT",
                        is_amendment=True, first_seen_at="2025-01-08T12:00:00Z", available_date="2025-01-07")
    seed([original, revised])
    response = client.post("/api/trading/backtests", headers=headers["admin"], json=backtest())
    assert response.status_code == 422
    assert storage.listing("run") == []


def test_original_observed_before_later_amendment_remains_eligible(context):
    client, headers, _ = context
    original = automatic(first_seen_at="2025-01-07T12:00:00Z", superseded_at="2025-01-10T04:59:59.999Z")
    revised = automatic(disclosure_id="cst:house:20000001:0:v2", version=2, symbol="MSFT",
                        is_amendment=True, first_seen_at="2025-01-10T12:00:00Z", available_date="2025-01-09")
    seed([original, revised])
    response = client.post("/api/trading/backtests", headers=headers["admin"], json=backtest())
    assert response.status_code == 201, response.text
    assert [fill["symbol"] for fill in response.json()["result"]["fills"]] == ["AAPL"]
    assert response.json()["result"]["fills"][0]["execution_date"] == "2025-01-08"


def test_exploratory_history_can_use_original_version_before_its_later_correction(context):
    client, headers, _ = context
    original = automatic(first_seen_at="2025-01-08T12:00:00Z", superseded_at="2025-01-08T04:59:59.999Z")
    revised = automatic(disclosure_id="cst:house:20000001:0:v2", version=2, symbol="MSFT",
                        is_amendment=True, first_seen_at="2025-01-08T12:00:00Z", available_date="2025-01-07")
    seed([original, revised])
    response = client.post("/api/trading/backtests", headers=headers["admin"],
                           json=backtest(allow_estimated_disclosure_dates=True))
    assert response.status_code == 201, response.text
    assert [fill["symbol"] for fill in response.json()["result"]["fills"]] == ["AAPL"]
    assert response.json()["result"]["fills"][0]["execution_date"] == "2025-01-07"


def test_successful_feed_cache_reuses_unchanged_checks_and_refreshes_on_data_revision(context):
    _, _, monkeypatch = context
    seed([automatic()])
    original_read = storage.read
    compact = storage._summary(original_read("congress-feed"))
    payload_reads = []
    def read(key):
        if key == "congress-feed":
            payload_reads.append(key)
        return original_read(key)
    # Model Postgres' independent summary column without touching a database.
    monkeypatch.setattr(storage, "read_summary", lambda _key: copy.deepcopy(compact))
    monkeypatch.setattr(storage, "read", read)
    assert congress.research_document()["records"][0]["symbol"] == "AAPL"
    assert len(payload_reads) == 1
    compact["collection"]["last_success"] = "2026-10-22T18:30:00Z"
    unchanged = congress.research_document()
    assert unchanged["records"][0]["symbol"] == "AAPL"
    assert unchanged["collection"]["last_success"] == "2026-10-22T18:30:00Z"
    assert len(payload_reads) == 1  # An unchanged six-hour check must not reload the large feed.
    def next_success(document):
        document["records"][0]["symbol"] = "MSFT"
        document["revision"] += 1
        document["collection"]["last_success"] = "2026-10-22T18:30:00Z"
        return document
    storage.mutate("congress-feed", next_success)
    compact["revision"] += 1  # Source SHA deliberately remains identical.
    assert congress.research_document()["records"][0]["symbol"] == "MSFT"
    assert len(payload_reads) == 2


def test_failed_refresh_status_is_current_while_cached_last_good_records_remain(context):
    client, headers, monkeypatch = context
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    source = seed([automatic()])
    before = congress.research_document()
    def failed_attempt(document):
        document["collection"].update(state="failed", last_attempt="2026-10-22T18:30:00Z",
                                      last_error="The source requires review; prior data is retained.")
        return document
    storage.mutate("congress-feed", failed_attempt)
    after = congress.research_document()
    assert after["records"] == before["records"]
    assert after["feed_snapshot"] == source
    assert after["collection"]["state"] == "failed"
    assert after["collection"]["last_attempt"] == "2026-10-22T18:30:00Z"
    browsed = client.get("/api/trading/congress", headers=headers["guest"]).json()
    assert browsed["collection"]["state"] == "failed"
    assert "source requires review" in browsed["collection"]["last_error"]
    assert browsed["records"][0]["symbol"] == "AAPL"


@pytest.mark.parametrize("automatic_owner,manual_owner", [
    ("self", "member"), ("spouse", "SP"), ("joint", "JT"), ("dependent_child", "dependent"),
])
def test_manual_copy_of_collected_evidence_is_hidden_and_cannot_bypass_first_seen(context, automatic_owner, manual_owner):
    client, headers, _ = context
    collected = automatic(owner=automatic_owner)
    manual = {key: collected[key] for key in congress.COLUMNS}
    manual.update(disclosure_id="manual-row", owner=manual_owner, amount_range="$1001-$15000", lag_days=4)
    seed([collected], [manual])
    document = congress.research_document()
    assert [row["disclosure_id"] for row in document["records"]] == [collected["disclosure_id"]]
    assert document["manual_duplicates_hidden"] == 1
    response = client.post("/api/trading/backtests", headers=headers["admin"], json=backtest())
    assert response.status_code == 422
    assert storage.read("congress")["records"] == [manual]  # Evidence is hidden, never deleted.


def test_different_household_owners_do_not_collapse_into_one_transaction(context):
    collected = automatic(owner="spouse")
    manual = {key: collected[key] for key in congress.COLUMNS}
    manual.update(disclosure_id="manual-row", owner="member", lag_days=4)
    seed([collected], [manual])
    document = congress.research_document()
    assert len(document["records"]) == 2
    assert document["manual_duplicates_hidden"] == 0


def test_unknown_assets_and_options_stay_visible_but_are_not_copied(context):
    client, headers, _ = context
    stock = automatic()
    option = automatic(disclosure_id="cst:house:20000001:1:v1", event_id="house:20000001:1", asset_type="option")
    other = automatic(disclosure_id="cst:house:20000001:2:v1", event_id="house:20000001:2", asset_type="other")
    seed([stock, option, other])
    assert client.get("/api/trading/congress", headers=headers["guest"]).json()["total"] == 3
    response = client.post("/api/trading/backtests", headers=headers["admin"],
                           json=backtest(allow_estimated_disclosure_dates=True))
    assert response.status_code == 201
    run = response.json()
    assert len(run["result"]["fills"]) == 1
    assert {row["disclosure_id"] for row in run["result"]["exclusions"]} == {option["disclosure_id"], other["disclosure_id"]}


def test_collection_endpoints_require_auth_and_only_admin_can_refresh(context):
    client, headers, monkeypatch = context
    calls = []
    monkeypatch.setattr(disclosure_collector, "collect", lambda **kwargs: calls.append(kwargs))
    assert client.get("/api/trading/congress/collection").status_code == 401
    assert client.post("/api/trading/congress/collection/refresh").status_code == 401
    for role in ("guest", "demo"):
        status = client.get("/api/trading/congress/collection", headers=headers[role])
        assert status.status_code == 200 and status.json()["state"] == "disabled"
        assert client.post("/api/trading/congress/collection/refresh", headers=headers[role]).status_code == 403
    disabled = client.post("/api/trading/congress/collection/refresh", headers=headers["admin"])
    assert disabled.status_code == 409
    assert calls == []


def test_admin_refresh_queues_background_collection_without_external_network(context):
    client, headers, monkeypatch = context
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    calls = []
    monkeypatch.setattr(disclosure_collector, "collect", lambda **kwargs: calls.append(kwargs))
    response = client.post("/api/trading/congress/collection/refresh", headers=headers["admin"])
    assert response.status_code == 202 and response.json()["state"] == "running"
    assert calls == [{"force": True}]


def test_refresh_does_not_queue_a_second_active_collection_or_expose_lease(context):
    client, headers, monkeypatch = context
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    seed([], collection={"state": "running", "lease_token": "private-lease-identifier",
                         "lease_expires_at": "2099-01-01T00:00:00Z"})
    calls = []
    monkeypatch.setattr(disclosure_collector, "collect", lambda **kwargs: calls.append(kwargs))
    response = client.post("/api/trading/congress/collection/refresh", headers=headers["admin"])
    assert response.status_code == 202
    assert calls == []
    assert "lease_token" not in response.text and "private-lease-identifier" not in response.text


def test_csv_cannot_impersonate_an_automatic_disclosure_id(context):
    client, headers, _ = context
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=congress.COLUMNS)
    writer.writeheader()
    writer.writerow({key: automatic()[key] for key in congress.COLUMNS})
    response = client.post("/api/trading/congress/import", headers=headers["admin"], json={"csv_text": buffer.getvalue()})
    assert response.status_code == 422 and "reserved" in response.json()["detail"]
    assert storage.read("congress") is None
