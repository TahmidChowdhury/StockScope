"""Offline comparison contracts: partial coverage and bounded provider work."""

import asyncio
from threading import Event, Lock, get_ident

import httpx
import pytest
from fastapi import FastAPI

from backend.core.auth import verify_password_with_role
from backend.models.fundamentals import CompareRequest
from backend.routers import fundamentals


def test_compare_normalizes_symbols_and_preserves_partial_coverage(monkeypatch):
    calls = []

    def compute(ticker):
        calls.append(ticker)
        if ticker == "FAIL":
            raise RuntimeError("Provider unavailable")
        if ticker == "EMPTY":
            return {}
        if ticker == "LIMITED":
            return {"ticker": ticker, "insufficient_data": True}
        return {"ticker": ticker, "insufficient_data": False,
                "revenue_ttm": {"BRK-B": 10, "AAPL": 10, "ZERO": 0, "NEG": -5}[ticker]}

    monkeypatch.setattr(fundamentals, "_compute_ttm_cached", compute)

    async def exercise():
        monkeypatch.setattr(fundamentals, "_screener_semaphore", asyncio.Semaphore(15))
        return await fundamentals.compare_fundamentals(CompareRequest(
            tickers=[" limited ", "brk.b", "BRK-B", "aapl", "ZERO", "NEG", "FAIL", "EMPTY"],
        ), "admin")

    results = asyncio.run(exercise())

    assert sorted(calls) == sorted(["LIMITED", "BRK-B", "AAPL", "ZERO", "NEG", "FAIL", "EMPTY"])
    assert [row["ticker"] for row in results] == ["BRK-B", "AAPL", "ZERO", "NEG", "LIMITED"]
    assert results[-1] == {"ticker": "LIMITED", "insufficient_data": True}
    assert results[2]["revenue_ttm"] == 0


def test_compare_runs_in_bounded_threads_without_blocking_event_loop(monkeypatch):
    lock = Lock()
    two_started = Event()
    release = Event()
    state = {"active": 0, "peak": 0, "threads": set()}
    main_thread = get_ident()

    def compute(ticker):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
            state["threads"].add(get_ident())
            if state["active"] == 2:
                two_started.set()
        try:
            if not release.wait(timeout=2):
                raise RuntimeError("The event loop did not release provider work")
            return {"ticker": ticker, "revenue_ttm": 1}
        finally:
            with lock:
                state["active"] -= 1

    monkeypatch.setattr(fundamentals, "_compute_ttm_cached", compute)

    async def exercise():
        monkeypatch.setattr(fundamentals, "_screener_semaphore", asyncio.Semaphore(2))
        task = asyncio.create_task(fundamentals.compare_fundamentals(
            CompareRequest(tickers=["AAA", "BBB", "CCC", "DDD", "EEE"]), "admin",
        ))
        try:
            # This coroutine can resume while both provider calls are blocked.
            assert await asyncio.wait_for(asyncio.to_thread(two_started.wait, 1), timeout=1.5)
        finally:
            release.set()
        return await task

    results = asyncio.run(exercise())
    assert [row["ticker"] for row in results] == ["AAA", "BBB", "CCC", "DDD", "EEE"]
    assert state["peak"] == 2
    assert main_thread not in state["threads"]


@pytest.mark.parametrize("tickers,status", [([], 400), (["AAPL"] * 21, 400), (["!INVALID"], 422)])
def test_compare_keeps_request_errors_as_client_errors(monkeypatch, tickers, status):
    def unexpected_provider_call(_):
        pytest.fail("Invalid input must be rejected before provider work")

    monkeypatch.setattr(fundamentals, "_compute_ttm_cached", unexpected_provider_call)
    app = FastAPI()
    app.include_router(fundamentals.router, prefix="/api/fundamentals")
    app.dependency_overrides[verify_password_with_role] = lambda: "admin"

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
            return await client.post("/api/fundamentals/compare", json={"tickers": tickers})

    response = asyncio.run(exercise())
    assert response.status_code == status
