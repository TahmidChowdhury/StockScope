"""Opt-in checks for an explicitly provisioned, disposable local PostgreSQL database.

Set STOCKSCOPE_TEST_DATABASE_URL to a migrated database whose name ends in _test.
No table/schema is dropped; fixture records are removed through the repository.
"""

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from backend.db import ResearchRepository
from backend.db.engine import create_database_engine
from backend.db.models import Base, ImportBatch, TradingDocument


@pytest.fixture(scope="module")
def repository():
    url = os.getenv("STOCKSCOPE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL test database was not configured")
    engine = create_database_engine(url)
    if not (engine.url.database or "").endswith("_test"):
        engine.dispose()
        pytest.fail("Refusing integration checks outside an explicitly named _test database")
    repository = ResearchRepository(engine)
    repository.check_ready()
    yield repository
    engine.dispose()


@pytest.fixture
def symbols(repository):
    values = ["T" + uuid4().hex[:7].upper(), "T" + uuid4().hex[:7].upper()]
    yield values
    for symbol in values:
        job = repository.get_latest_run(symbol)
        if job and job["status"] in {"pending", "processing"}:
            repository.update_run(job["run_id"], status="failed", progress=100, message="Fixture cleanup")
        repository.delete_symbol_research(symbol)


def test_postgres_rls_and_anonymous_privileges(repository):
    with repository.engine.begin() as connection:
        # These roles only exist inside the user-provisioned disposable test cluster.
        for role in ("anon", "authenticated"):
            connection.execute(text(f"""DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    CREATE ROLE "{role}" NOLOGIN;
                END IF;
            END $$"""))
        rows = connection.execute(text("SELECT relname, relrowsecurity FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'")).all()
        flags = dict(rows)
        for table in list(Base.metadata.tables) + ["alembic_version"]:
            assert flags[table], f"RLS not enabled on {table}"
            for role in ("anon", "authenticated"):
                assert not connection.scalar(text("SELECT has_table_privilege(:role, :table, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')"), {"role": role, "table": table})
        assert connection.scalar(text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = ANY(:tables)"), {"tables": list(Base.metadata.tables)}) == 0
    with repository.engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("SET LOCAL ROLE anon"))
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT payload FROM snapshot_revisions LIMIT 1"))
        transaction.rollback()


def test_postgres_owner_roundtrip_and_rls_even_if_select_is_granted(repository, symbols):
    symbol = symbols[0]
    records = [{"title": "Fixture evidence", "publishedAt": "2020-01-01T00:00:00Z", "fetched_at": "2020-01-02T00:00:00Z"}]
    reference = repository.save_snapshot(symbol, "news_sentiment", records)
    assert repository.read_snapshot_reference(reference) == records
    assert repository.load_snapshots(symbol) == [("news_sentiment", records)]
    with repository.engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("GRANT SELECT ON snapshot_revisions TO anon"))
        connection.execute(text("SET LOCAL ROLE anon"))
        assert connection.scalar(text("SELECT count(*) FROM snapshot_revisions")) == 0
        transaction.rollback()  # Restore the restricted privilege, even on test failure via connection close.


def test_postgres_concurrent_job_creation_claims_only_once(repository, symbols):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: repository.create_run(symbols[0], ["news"]), range(8)))
    assert sum(result["created"] for result in results) == 1
    assert len({result["run_id"] for result in results}) == 1


def test_postgres_disclosure_lease_prevents_overlapping_source_requests(repository, monkeypatch):
    from backend import trading
    from backend.services import research
    from backend.trading import disclosure_collector as collector
    key = f"run-{uuid4()}"
    monkeypatch.setattr(collector, "DOCUMENT_ID", key)
    monkeypatch.setattr(research, "repository", lambda: repository)
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    started, release = threading.Event(), threading.Event()
    requests = []
    def fetch(**kwargs):
        requests.append(1)
        started.set()
        assert release.wait(timeout=15)
        return {"records": [{"disclosure_id": "fixture:v1", "event_id": "fixture", "version": 1,
                             "symbol": "AAPL", "superseded_at": None}],
                "metadata": {"revision": "fixture"}, "unchanged": False}
    monkeypatch.setattr(trading, "disclosure_source", SimpleNamespace(fetch_snapshot=fetch), raising=False)
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            first = executor.submit(collector.collect, force=True)
            try:
                assert started.wait(timeout=10)
                others = list(executor.map(lambda _: collector.collect(force=True), range(4)))
                assert all(result["state"] == "running" for result in others)
                assert requests == [1]
            finally:
                release.set()
            assert first.result(timeout=10)["state"] == "completed"
    finally:
        with repository.engine.begin() as connection:
            connection.execute(TradingDocument.__table__.delete().where(TradingDocument.id == key))


def test_postgres_collection_metadata_does_not_select_the_history_payload(repository, monkeypatch):
    from backend import trading
    from backend.services import research
    from backend.trading import disclosure_collector as collector, storage
    key = f"run-{uuid4()}"
    monkeypatch.setattr(collector, "DOCUMENT_ID", key)
    monkeypatch.setattr(research, "repository", lambda: repository)
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    source = SimpleNamespace(fetch_snapshot=lambda **kwargs: {
        "records": [{"disclosure_id": "fixture:v1", "event_id": "fixture", "version": 1,
                     "symbol": "AAPL", "superseded_at": None}],
        "metadata": {"revision": "fixture"}, "unchanged": False})
    monkeypatch.setattr(trading, "disclosure_source", source, raising=False)
    statements = []
    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    try:
        assert collector.collect(force=True)["state"] == "completed"
        original = storage.read(key)
        event.listen(repository.engine, "before_cursor_execute", capture)
        try:
            source.fetch_snapshot = lambda **kwargs: {"records": [], "metadata": kwargs["previous"], "unchanged": True}
            unchanged = collector.collect(force=True)
            assert unchanged["counts"]["unchanged"] is True
            assert unchanged["data_revision"] == original["revision"]
            def fail(**kwargs):
                raise RuntimeError("private upstream diagnostic")
            source.fetch_snapshot = fail
            assert collector.collect(force=True)["state"] == "failed"
            assert collector.status()["row_count"] == 1
        finally:
            event.remove(repository.engine, "before_cursor_execute", capture)
        # Selecting payload->'collection' is small; selecting the payload column
        # itself would download every historical row on each unchanged check.
        assert statements
        assert not any(re.search(r"(?:SELECT\s+|,\s*)trading_documents\.payload(?:\s*,|\s+FROM|\s+AS)",
                                 statement, re.IGNORECASE) for statement in statements)
        after = storage.read(key)
        assert after["records"] == original["records"]
        assert after["source"] == original["source"]
        assert after["revision"] == original["revision"]
    finally:
        with repository.engine.begin() as connection:
            connection.execute(TradingDocument.__table__.delete().where(TradingDocument.id == key))


def test_postgres_concurrent_identical_import_is_applied_once(repository, symbols):
    manifest = uuid4().hex
    snapshots = [(symbols[0], "news_sentiment", [{"title": "Fixture import"}])]
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: repository.import_snapshots(snapshots, manifest), range(4)))
        assert sum(result["applied"] for result in results) == 1
        assert len({result["batch_id"] for result in results}) == 1
    finally:
        repository.delete_symbol_research(symbols[0])
        with repository.engine.begin() as connection:
            connection.execute(ImportBatch.__table__.delete().where(ImportBatch.manifest_hash == manifest))


def test_postgres_explicit_delete_keeps_another_symbols_shared_article(repository, symbols):
    records = [{"url": f"https://example.org/{uuid4().hex}", "title": "Shared fixture"}]
    first = repository.save_snapshot(symbols[0], "news_sentiment", records)
    second = repository.save_snapshot(symbols[1], "news_sentiment", records)
    repository.delete_symbol_research(symbols[0])
    with pytest.raises(KeyError):
        repository.read_snapshot_reference(first)
    assert repository.read_snapshot_reference(second) == records
