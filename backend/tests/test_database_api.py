"""Storage/API integration with migrated disposable databases and no network."""

import asyncio
import importlib
import json
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.exc import OperationalError

from backend.db import ResearchRepository
from backend.db.engine import create_database_engine
from backend.services import research


@pytest.fixture
def context(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_PASSWORD", "fixture-admin")
    monkeypatch.setenv("DEMO_PASSWORD", "fixture-demo")
    monkeypatch.setenv("GUEST_PASSWORD", "fixture-guest")
    monkeypatch.setenv("SECRET_KEY", "fixture-signing-key-not-a-password-1234567890")
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path / "files"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    engine = create_database_engine(f"sqlite:///{tmp_path / 'research.db'}", allow_sqlite=True)
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        workspace_config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'), ini_section='workspace')
        workspace_config.attributes['connection'] = connection
        command.upgrade(workspace_config, 'head')
    repo = ResearchRepository(engine)
    import backend.db
    monkeypatch.setattr(backend.db, "get_repository", lambda: repo)
    api = importlib.import_module("backend.api")
    api.analysis_status.clear()
    api.cache.invalidate()
    yield api, repo, tmp_path
    api.analysis_status.clear()
    api.cache.invalidate()
    engine.dispose()


def test_database_evidence_reads_ignore_local_snapshots(context):
    api, repo, directory = context
    files = directory / "files"
    files.mkdir()
    (files / "MSFT_news_sentiment.json").write_text(json.dumps([{"title": "Disk only"}]))
    records = [
        {"title": "Reported news", "source": "Publisher", "publishedAt": "2020-01-01", "sentiment": {"compound": .2}},
        {"title": "Company statement", "source_type": "company_release", "source": "Company", "sentiment": {"compound": 1}},
        {"title": "Discovered article", "source": "GDELT", "provider_seen_at": "2026-10-14T10:00:00Z"},
    ]
    reference = research.save_records("AAPL", "comprehensive_news", records)
    assert reference.startswith("db://")
    assert api._produced_records({"reference": reference}) == 3
    assert api.get_available_tickers() == ["AAPL"]
    assert research.saved_news("MSFT") == []
    frame = research.load_evidence("AAPL")
    assert research.sentiment_metrics(frame)["sample_size"] == 1
    assert research.sentiment_metrics(frame)["avg_sentiment"] == .2
    assert frame[frame["title"] == "Discovered article"]["created_utc"].isna().all()
    assert frame[frame["title"] == "Company statement"]["compound"].isna().all()
    assert list(files.glob("AAPL*")) == []


def test_persisted_jobs_survive_memory_reset_and_keep_provider_failures(context, monkeypatch):
    api, repo, _ = context
    reference = research.save_records("AAPL", "news_sentiment", [{"title": "Saved"}])
    monkeypatch.setattr(api, "_collect_news", lambda symbol: {
        "reference": reference,
        "providers": {"gdelt": {"status": "failed", "count": 0}, "company_ir_rss": {"status": "ok", "count": 1}},
    })
    async def exercise():
        tasks = BackgroundTasks()
        await api.analyze_stock(api.StockRequest(symbol="AAPL", sources=["news"]), tasks, "member")
        await api.analyze_stock(api.StockRequest(symbol="AAPL", sources=["news"]), tasks, "member")
        assert len(tasks.tasks) == 1
        await tasks()
        api.analysis_status.clear()
        job = await api.get_analysis_status("AAPL", "demo")
        assert job.status == "partial"
        assert job.providers["news.gdelt"]["status"] == "failed"
        assert job.providers["news"]["count"] == 1
        assert job.run_id and job.completed_at
        assert repo.get_run(job.run_id)["status"] == "partial"
    asyncio.run(exercise())


def test_concurrent_admission_respects_four_job_limit(context):
    api, _, _ = context
    async def exercise():
        tasks = BackgroundTasks()
        responses = await asyncio.gather(*[
            api.analyze_stock(api.StockRequest(symbol=symbol, sources=["news"]), tasks, "member")
            for symbol in ["AAPL", "MSFT", "NVDA", "META", "TSLA", "GOOG"]
        ], return_exceptions=True)
        assert len(tasks.tasks) == 4
        errors = [result for result in responses if isinstance(result, HTTPException)]
        assert len(errors) == 2 and all(error.status_code == 429 for error in errors)
    asyncio.run(exercise())


def test_restart_marks_unfinished_work_failed_and_explicit_delete_purges(context):
    api, repo, _ = context
    reference = research.save_records("AAPL", "news_sentiment", [{"title": "Saved"}])
    repo.create_run("AAPL", ["news"])
    async def exercise():
        with pytest.raises(HTTPException) as error:
            await api.delete_stock("AAPL", "admin")
        assert error.value.status_code == 409
        async with api.lifespan(api.app):
            job = await api.get_analysis_status("AAPL", "demo")
            assert job.status == "failed"
            assert job.completed_at
        assert (await api.delete_stock("AAPL", "admin"))["success"]
    asyncio.run(exercise())
    assert research.list_saved_symbols() == []
    assert repo.get_latest_run("AAPL") is None
    with pytest.raises(KeyError):
        repo.read_snapshot_reference(reference)


def test_lifespan_starts_and_stops_configured_disclosure_scheduler(context, monkeypatch):
    api, _, _ = context
    from backend.trading import disclosure_collector
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "true")
    async def exercise():
        started = asyncio.Event()
        async def scheduler(stop):
            started.set()
            await stop.wait()
        monkeypatch.setattr(disclosure_collector, "run_scheduler", scheduler)
        async with api.lifespan(api.app):
            await asyncio.wait_for(started.wait(), timeout=1)
            task = api.app.state.disclosure_collection_task
            assert not task.done()
        assert task.done()
    asyncio.run(exercise())


def test_storage_failure_never_falls_back_to_local_files(context, monkeypatch):
    api, repo, directory = context
    files = directory / "files"
    files.mkdir()
    (files / "AAPL_news_sentiment.json").write_text('[{"title":"Disk fallback must not appear"}]')
    def fail(*args, **kwargs):
        raise OperationalError("fixture", {}, RuntimeError("offline"))
    monkeypatch.setattr(repo, "list_symbols", lambda: ["AAPL"])
    monkeypatch.setattr(repo, "load_snapshots", fail)
    monkeypatch.setattr(repo, "list_company_summaries", fail)
    monkeypatch.setattr(repo, "check_ready", fail)
    from backend.core.auth import create_access_token
    headers = {"Authorization": f"Bearer {create_access_token('fixture', 'admin')}"}
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://fixture") as client:
            response = await client.get("/api/stocks/AAPL/news", headers=headers)
            assert response.status_code == 503
            assert "Disk fallback" not in response.text
            assert (await client.get("/health")).status_code == 503
            assert (await client.get("/api/stocks", headers=headers)).status_code == 503
    asyncio.run(exercise())


def test_sec_collection_saves_facts_and_failure_preserves_snapshot(context, monkeypatch):
    api, _, _ = context
    from backend.services import sec_facts
    envelope = {"symbol": "AAPL", "status": "completed", "facts": [{
        "fact_id": "fixture", "taxonomy": "us-gaap", "concept": "Assets", "unit": "USD", "value": 123,
        "end": "2024-12-31", "filed": "2025-02-01", "accession": "0001-25-000001", "form": "10-K",
    }], "filings": [{"form": "10-K", "filed": "2025-02-01", "accession": "0001-25-000001", "filing_url": "https://www.sec.gov/Archives/fixture"}], "metadata": {}}
    monkeypatch.setattr(sec_facts, "collect_sec_facts", lambda symbol: envelope)
    assert api._collect_sec_facts("AAPL") == envelope
    assert research.saved_sec_facts("AAPL") == envelope
    events = research.filing_events(research.load_evidence("AAPL"))
    assert len(events) == 1
    assert events[0]["form_type"] == "10-K"
    assert events[0]["filing_date"] == "2025-02-01"
    assert events[0]["url"] == "https://www.sec.gov/Archives/fixture"
    monkeypatch.setattr(sec_facts, "collect_sec_facts", lambda symbol: {"status": "not_configured", "facts": [], "filings": []})
    async def exercise():
        tasks = BackgroundTasks()
        await api.analyze_stock(api.StockRequest(symbol="AAPL", sources=["sec_facts"]), tasks, "member")
        await tasks()
        job = await api.get_analysis_status("AAPL", "demo")
        assert job.status == "failed"
        assert job.providers["sec_facts"]["status"] == "not_configured"
    asyncio.run(exercise())
    assert research.saved_sec_facts("AAPL") == envelope


def test_status_recovers_terminal_write_after_database_outage(context, monkeypatch):
    api, repo, _ = context
    original_update = repo.update_run
    def offline(*args, **kwargs):
        raise OperationalError("fixture", {}, RuntimeError("offline"))
    async def exercise():
        tasks = BackgroundTasks()
        await api.analyze_stock(api.StockRequest(symbol="AAPL", sources=["news"]), tasks, "member")
        run_id = api.analysis_status["AAPL"].run_id
        monkeypatch.setattr(repo, "update_run", offline)
        await tasks()
        assert api.analysis_status["AAPL"].status == "failed"
        assert repo.get_run(run_id)["status"] == "pending"
        monkeypatch.setattr(repo, "update_run", original_update)
        assert (await api.get_analysis_status("AAPL", "demo")).status == "failed"
        from backend.core.resources import state
        with state('provider:refresh') as usage:
            usage['symbols'] = {}  # Simulate the cooldown elapsing before the retry.
        next_tasks = BackgroundTasks()
        await api.analyze_stock(api.StockRequest(symbol="AAPL", sources=["news"]), next_tasks, "member")
        assert len(next_tasks.tasks) == 1
        assert api.analysis_status["AAPL"].run_id != run_id
    asyncio.run(exercise())
