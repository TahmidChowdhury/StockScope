"""Collector persistence, concurrency, source drift and scheduler tests without network."""
import asyncio
import copy
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from backend.db.engine import create_database_engine
from backend.db.repository import ResearchRepository
from backend.db.models import TradingDocument
from backend.services import research
from backend import trading
from backend.trading import disclosure_collector as collector, storage


def snapshot(**changes):
    row = {"disclosure_id": "cst:event-1:v1", "event_id": "event-1", "version": 1,
           "member": "Example Member", "symbol": "AAPL", "side": "buy",
           "available_date": "2025-01-06", "transaction_date": "2025-01-02",
           "superseded_at": None, "content_hash": "source-generated-hash"}
    return {"records": [row], "metadata": {"revision": "revision-1", "years": [2025, 2026],
            "provider": "Public disclosure dataset"}, "unchanged": False, **changes}


@pytest.fixture(params=["file", "database"])
def context(request, monkeypatch, tmp_path):
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    monkeypatch.setenv("DISCLOSURE_COLLECTION_INTERVAL_HOURS", "6")
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path / "data"))
    engine, repo = None, None
    if request.param == "database":
        engine = create_database_engine(f"sqlite:///{tmp_path / 'disclosures.db'}", allow_sqlite=True)
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            workspace_config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'), ini_section='workspace')
            workspace_config.attributes['connection'] = connection
            command.upgrade(workspace_config, 'head')
        repo = ResearchRepository(engine)
    monkeypatch.setattr(research, "repository", lambda: repo)
    current = [datetime(2026, 10, 22, 14, tzinfo=timezone.utc)]
    monkeypatch.setattr(collector, "utcnow", lambda: current[0])
    source = SimpleNamespace(fetch_snapshot=lambda **kwargs: copy.deepcopy(snapshot()))
    monkeypatch.setattr(trading, "disclosure_source", source, raising=False)
    yield source, current, repo
    if engine:
        engine.dispose()


def test_configuration_defaults_and_force_does_not_enable_collection(monkeypatch, context):
    source, _, _ = context
    monkeypatch.delenv("DISCLOSURE_COLLECTION_ENABLED")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert not collector.enabled()
    monkeypatch.setenv("DATABASE_URL", "configured-but-not-read-by-this-test")
    assert collector.enabled()
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "false")
    source.fetch_snapshot = lambda **kwargs: pytest.fail("Disabled collector made a network request")
    assert collector.collect(force=True)["state"] == "disabled"
    assert storage.read(collector.DOCUMENT_ID) is None


def test_first_hydration_repeat_and_unchanged_preserve_observation_time(context):
    source, clock, repository = context
    first = collector.collect()
    assert first["state"] == "completed"
    assert first["row_count"] == 1
    assert first["counts"]["inserted"] == 1
    assert first["data_revision"] == 1
    assert first["next_run"] == (clock[0] + timedelta(hours=6)).isoformat()
    assert "lease_token" not in first
    assert collector.status() == first
    compact = storage.read_summary(collector.DOCUMENT_ID)
    assert compact["row_count"] == 1
    assert "records" not in compact
    assert "lease_token" not in compact["collection"]
    if repository is not None:
        with Session(repository.engine) as session:
            assert session.get(TradingDocument, collector.DOCUMENT_ID).kind == "congress_feed"
    original = storage.read(collector.DOCUMENT_ID)["records"][0]
    assert original["first_seen_at"] == clock[0].isoformat() == original["observed_at"]
    assert storage.read("congress") is None
    clock[0] += timedelta(minutes=1)
    repeated = collector.collect(force=True)
    assert repeated["counts"]["duplicates"] == 1
    assert repeated["counts"]["inserted"] == 0
    again = storage.read(collector.DOCUMENT_ID)["records"][0]
    assert again["first_seen_at"] == original["first_seen_at"]
    assert again["last_seen_at"] == clock[0].isoformat()
    previous = []
    def unchanged(**kwargs):
        previous.append(kwargs["previous"])
        return snapshot(records=[], unchanged=True)
    source.fetch_snapshot = unchanged
    assert collector.collect(force=True)["counts"]["unchanged"] is True
    assert previous == [first["source"]]
    assert storage.read(collector.DOCUMENT_ID)["records"][0] == again
    assert collector.status()["data_revision"] == repeated["data_revision"]


def test_metadata_updates_preserve_history_and_fence_old_leases(context):
    _, clock, _ = context
    collector.collect()
    original = storage.read(collector.DOCUMENT_ID)["records"]
    metadata = storage.mutate_feed_metadata(collector.DOCUMENT_ID,
        lambda previous: collector._claim(previous, "old-worker", clock[0], True))
    assert "records" not in metadata
    assert metadata["row_count"] == len(original)
    clock[0] += timedelta(seconds=collector.LEASE_SECONDS + 1)
    storage.mutate_feed_metadata(collector.DOCUMENT_ID,
        lambda previous: collector._claim(previous, "new-worker", clock[0], True))
    storage.mutate_feed_metadata(collector.DOCUMENT_ID,
        lambda previous: collector._finish(previous, "old-worker", clock[0], error="Old attempt failed"))
    after = storage.read(collector.DOCUMENT_ID)
    assert after["records"] == original
    assert after["collection"]["lease_token"] == "new-worker"
    assert collector.status()["data_revision"] == 1


def test_not_due_does_not_fetch_and_failures_retain_data_and_retry(context):
    source, clock, _ = context
    first = collector.collect()
    source.fetch_snapshot = lambda **kwargs: pytest.fail("The source should not be requested before it is due")
    assert collector.collect() == first
    clock[0] += timedelta(hours=6)
    def fail(**kwargs):
        raise RuntimeError("https://private.example/?token=TOP_SECRET")
    source.fetch_snapshot = fail
    failed = collector.collect()
    assert failed["state"] == "failed"
    assert failed["row_count"] == 1
    assert failed["last_success"] == first["last_success"]
    assert "TOP_SECRET" not in str(failed)
    assert failed["next_run"] == (clock[0] + timedelta(minutes=5)).isoformat()
    assert collector.collect(force=True)["next_run"] == (clock[0] + timedelta(minutes=10)).isoformat()
    assert storage.read(collector.DOCUMENT_ID)["records"][0]["symbol"] == "AAPL"


def test_expired_lease_can_be_replaced_and_stale_worker_cannot_commit(context):
    _, clock, _ = context
    original = storage.mutate(collector.DOCUMENT_ID, lambda previous: collector._claim(previous, "old-worker", clock[0], False))
    assert collector.status(original)["state"] == "running"
    clock[0] += timedelta(seconds=collector.LEASE_SECONDS + 1)
    assert collector.status(original)["state"] == "interrupted"
    new = storage.mutate(collector.DOCUMENT_ID, lambda previous: collector._claim(previous, "new-worker", clock[0], False))
    assert new["collection"]["lease_token"] == "new-worker"
    stale = storage.mutate(collector.DOCUMENT_ID, lambda previous: collector._finish(previous, "old-worker", clock[0], snapshot=snapshot()))
    assert stale["records"] == []
    assert stale["collection"]["lease_token"] == "new-worker"
    assert collector.collect(force=True)["state"] == "running"


def test_concurrent_attempts_fetch_only_once(context):
    source, _, repo = context
    if repo is not None:
        pytest.skip("SQLite does not provide PostgreSQL SELECT FOR UPDATE locking")
    started, release = threading.Event(), threading.Event()
    calls = []
    def fetch(**kwargs):
        calls.append(1)
        started.set()
        assert release.wait(timeout=10)
        return snapshot()
    source.fetch_snapshot = fetch
    result = []
    worker = threading.Thread(target=lambda: result.append(collector.collect(force=True)))
    worker.start()
    try:
        assert started.wait(timeout=5)
        assert collector.collect(force=True)["state"] == "running"
        assert calls == [1]
    finally:
        release.set()
        worker.join(timeout=10)
    assert not worker.is_alive()
    assert result[0]["state"] == "completed"


def test_supersession_preserves_original_version_and_economic_drift_rolls_back(context):
    source, clock, _ = context
    collector.collect()
    first_seen = storage.read(collector.DOCUMENT_ID)["records"][0]["first_seen_at"]
    changed = snapshot()
    changed["records"][0]["superseded_at"] = "2026-10-23T12:00:00Z"
    replacement = {**changed["records"][0], "disclosure_id": "cst:event-1:v2", "version": 2,
                   "symbol": "MSFT", "superseded_at": None}
    changed["records"].append(replacement)
    source.fetch_snapshot = lambda **kwargs: copy.deepcopy(changed)
    clock[0] += timedelta(days=1)
    result = collector.collect(force=True)
    assert result["state"] == "completed"
    assert result["counts"] == {"inserted": 1, "duplicates": 1, "superseded": 1, "unchanged": False}
    records = storage.read(collector.DOCUMENT_ID)["records"]
    assert records[0]["first_seen_at"] == first_seen
    assert records[0]["supersession_observed_at"] == clock[0].isoformat()
    assert records[1]["first_seen_at"] == clock[0].isoformat()
    changed["records"][0]["symbol"] = "NVDA"
    failed = collector.collect(force=True)
    assert failed["state"] == "failed"
    assert "changed an existing disclosure version" in failed["last_error"]
    assert storage.read(collector.DOCUMENT_ID)["records"] == records


def test_capacity_failure_retains_all_history(context, monkeypatch):
    source, _, _ = context
    collector.collect()
    prior = storage.read(collector.DOCUMENT_ID)["records"]
    changed = snapshot()
    changed["records"][0].update(disclosure_id="cst:event-2:v1", event_id="event-2")
    source.fetch_snapshot = lambda **kwargs: changed
    monkeypatch.setattr(collector, "MAX_RECORDS", 1)
    failed = collector.collect(force=True)
    assert failed["state"] == "failed"
    assert "capacity" in failed["last_error"]
    assert storage.read(collector.DOCUMENT_ID)["records"] == prior


@pytest.mark.parametrize("excluded", [{}, {"missing_ticker": 1}])
def test_removed_or_newly_excluded_disclosure_rejects_new_source_revision(context, excluded):
    source, _, _ = context
    initial = snapshot()
    initial["records"][0]["provider_available_at"] = "2026-10-21T03:59:59Z"
    initial["records"].append({**initial["records"][0], "disclosure_id": "cst:event-2:v1", "event_id": "event-2"})
    source.fetch_snapshot = lambda **kwargs: copy.deepcopy(initial)
    collector.collect()
    prior = storage.read(collector.DOCUMENT_ID)
    changed = copy.deepcopy(initial)
    changed["records"] = changed["records"][1:]
    changed["metadata"].update(revision="revision-2", excluded_counts=excluded)
    source.fetch_snapshot = lambda **kwargs: changed
    failed = collector.collect(force=True)
    assert failed["state"] == "failed"
    assert "removed or excluded" in failed["last_error"]
    after = storage.read(collector.DOCUMENT_ID)
    assert after["records"] == prior["records"]
    assert after["source"] == prior["source"]
    assert after["collection"]["last_success"] == prior["collection"]["last_success"]


def test_year_rollover_retains_history_outside_the_current_fetch_scope(context):
    source, clock, _ = context
    initial = snapshot()
    initial["records"][0]["provider_available_at"] = "2025-12-31T23:59:59Z"
    initial["records"].append({**initial["records"][0], "disclosure_id": "cst:event-2:v1", "event_id": "event-2",
                               "provider_available_at": "2026-10-21T03:59:59Z"})
    source.fetch_snapshot = lambda **kwargs: copy.deepcopy(initial)
    collector.collect()
    old = storage.read(collector.DOCUMENT_ID)["records"][0]
    clock[0] = datetime(2027, 1, 2, 12, tzinfo=timezone.utc)
    changed = copy.deepcopy(initial)
    changed["records"] = changed["records"][1:]
    changed["metadata"].update(revision="revision-2", years=[2026, 2027])
    source.fetch_snapshot = lambda **kwargs: changed
    completed = collector.collect(force=True)
    assert completed["state"] == "completed"
    assert completed["row_count"] == 2
    after = storage.read(collector.DOCUMENT_ID)
    assert after["source"]["revision"] == "revision-2"
    assert after["records"][0] == old


def test_scheduler_survives_storage_failure_and_stops_without_another_attempt(monkeypatch):
    attempts = []
    async def exercise():
        stop = asyncio.Event()
        def collect(**kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                raise OSError("private storage detail")
            stop.set()
        monkeypatch.setattr(collector, "collect", collect)
        monkeypatch.setattr(collector, "status", lambda: {"enabled": True, "next_run": None})
        monkeypatch.setattr(collector, "POLL_SECONDS", 0.001)
        task = asyncio.create_task(collector.run_scheduler(stop))
        await asyncio.wait_for(task, timeout=5)
        await collector.stop_scheduler(task, stop)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(exercise())
    finally:
        loop.close()
    assert len(attempts) == 2


def test_scheduler_waits_for_persisted_due_time_and_shutdown_wakes_it(monkeypatch):
    attempts = []
    state = {"enabled": True, "next_run": None}
    async def exercise():
        stop = asyncio.Event()
        def collect(**kwargs):
            attempts.append(1)
            state["next_run"] = (collector.utcnow() + timedelta(hours=6)).isoformat()
            return state
        monkeypatch.setattr(collector, "collect", collect)
        monkeypatch.setattr(collector, "status", lambda: dict(state))
        monkeypatch.setattr(collector, "POLL_SECONDS", 0.001)
        task = asyncio.create_task(collector.run_scheduler(stop))
        for _ in range(100):
            if attempts:
                break
            await asyncio.sleep(0.001)
        await asyncio.sleep(0.01)
        await collector.stop_scheduler(task, stop)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(exercise())
    finally:
        loop.close()
    assert len(attempts) == 1


def test_scheduler_observes_an_earlier_retry_set_by_an_external_refresh(monkeypatch):
    attempts, checks = [], []
    state = {"enabled": True, "next_run": (collector.utcnow() + timedelta(hours=6)).isoformat()}
    async def exercise():
        stop = asyncio.Event()
        def status():
            checks.append(1)
            return dict(state)
        def collect(**kwargs):
            attempts.append(1)
            stop.set()
            return state
        monkeypatch.setattr(collector, "status", status)
        monkeypatch.setattr(collector, "collect", collect)
        monkeypatch.setattr(collector, "POLL_SECONDS", 0.001)
        task = asyncio.create_task(collector.run_scheduler(stop))
        for _ in range(100):
            if checks:
                break
            await asyncio.sleep(0.001)
        assert not attempts
        # An admin/CLI attempt failed while this process was waiting for six hours.
        state["next_run"] = (collector.utcnow() - timedelta(seconds=1)).isoformat()
        await asyncio.wait_for(task, timeout=5)
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(exercise())
    finally:
        loop.close()
    assert attempts == [1]
