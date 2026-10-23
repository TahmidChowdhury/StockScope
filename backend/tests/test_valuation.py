"""Offline contracts for evidence units, period validity, auth and provider limits."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Event, Lock

from cachetools import TTLCache
from fastapi import FastAPI
import httpx
import pytest

from backend.core.auth import verify_password_with_role
from backend.routers import valuation as router
from backend.services import valuation as service

NOW = datetime(2026, 10, 22, 16, tzinfo=timezone.utc)


def observations():
    period = {"basis": "ttm", "period_end": "2026-06-30", "quarter_ends": ["2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]}
    fundamentals = {"metadata": {"retrieved_at": NOW.isoformat(), "source": service.SOURCE}, "ttm": {
        "revenue_ttm": 1000, "fcf_ttm": -20, "ebitda_ttm": 200,
        "operating_margin_ttm": 0, "fcf_margin_ttm": -0.02,
        "revenue_growth_yoy": 0.1, "fcf_growth_yoy": -0.2, "debt_to_cash": 0,
        "period_metadata": {key: deepcopy(period) for key in ("revenue_ttm", "fcf_ttm", "ebitda_ttm", "operating_income_ttm")},
        "growth_metadata": {key: {"basis": "fiscal_year", "current_period_end": "2026-06-30", "prior_period_end": "2025-06-30"} for key in ("revenue_growth_yoy", "fcf_growth_yoy")},
    }}
    info = {"currency": "USD", "financialCurrency": "USD", "regularMarketPrice": 50,
            "regularMarketTime": NOW.timestamp() - 60, "marketCap": 2000, "enterpriseValue": 2400, "sharesOutstanding": 40}
    return fundamentals, info


def metrics(result):
    return {row["key"]: row for row in result["valuation"] + result["quality"]}


def test_calculates_only_comparable_ratios_and_preserves_losses_and_zeroes():
    fundamentals, info = observations()
    result = service.build_valuation("AAPL", fundamentals, info, now=NOW)
    rows = metrics(result)
    assert rows["fcf_yield"]["value"] == -0.01
    assert rows["ev_sales"]["value"] == 2.4
    assert rows["ev_ebitda"]["value"] == 12
    assert rows["operating_margin"]["value"] == 0
    assert rows["fcf_margin"]["value"] == -0.02
    assert rows["debt_cash"]["value"] == 0
    assert rows["debt_cash"]["status"] == "unknown"
    assert rows["fcf_growth"]["value"] == -0.2
    assert rows["fcf_growth"]["basis"] == "fiscal_year"
    assert rows["fcf_growth"]["prior_period_end"] == "2025-06-30"
    assert result["quote"]["price_at"] == "2026-10-22T15:59:00+00:00"
    assert result["financials"]["currency_basis"] == "provider financialCurrency declaration"
    assert result["source"] == service.SOURCE
    assert "not verified FCFF or FCFE" in result["methodology"]["fcf"]


@pytest.mark.parametrize("quote_currency,financial_currency", [("USD", "EUR"), ("USD", None), (None, "USD"), ("GBp", "GBP"), ("usd", "USD"), ("FOO", "FOO")])
def test_no_cross_currency_ratios_without_exact_supported_units(quote_currency, financial_currency):
    fundamentals, info = observations()
    info.update(currency=quote_currency, financialCurrency=financial_currency)
    result = service.build_valuation("AAPL", fundamentals, info, now=NOW)
    assert not result["financials"]["currency_compatible"]
    assert all(row["value"] is None and row["status"] == "unknown" for row in result["valuation"])
    assert metrics(result)["fcf_margin"]["value"] == -0.02


@pytest.mark.parametrize("price,time,status", [(0, NOW.timestamp(), "missing"), (None, NOW.timestamp(), "missing"),
    (50, None, "unknown"), (50, NOW.timestamp() + 600, "unknown"), (50, NOW.timestamp() - 5 * 86400, "stale")])
def test_quote_freshness_is_not_confused_with_fetch_time(price, time, status):
    fundamentals, info = observations()
    info.update(regularMarketPrice=price, regularMarketTime=time)
    result = service.build_valuation("AAPL", fundamentals, info, now=NOW)
    assert result["quote"]["status"] == status
    assert all(row["value"] is None for row in result["valuation"])
    assert result["fetched_at"] == NOW.isoformat()


@pytest.mark.parametrize("mutation", ["missing", "old", "future", "gap", "duplicate", "annual"])
def test_requires_consecutive_recent_ttm_periods(mutation):
    fundamentals, info = observations()
    period = fundamentals["ttm"]["period_metadata"]["revenue_ttm"]
    if mutation == "missing":
        period.clear()
    elif mutation == "old":
        period.update(period_end="2025-06-30", quarter_ends=["2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30"])
    elif mutation == "future":
        period.update(period_end="2027-06-30", quarter_ends=["2026-09-30", "2026-12-31", "2027-03-31", "2027-06-30"])
    elif mutation == "gap":
        period["quarter_ends"][0] = "2025-06-30"
    elif mutation == "duplicate":
        period["quarter_ends"][0] = period["quarter_ends"][1]
    else:
        period["basis"] = "fiscal_year"
    rows = metrics(service.build_valuation("AAPL", fundamentals, info, now=NOW))
    assert rows["ev_sales"]["value"] is None
    assert rows["fcf_yield"]["value"] == -0.01


def test_non_positive_ebitda_multiple_withheld_but_negative_enterprise_value_preserved():
    fundamentals, info = observations()
    fundamentals["ttm"]["ebitda_ttm"] = -10
    info["enterpriseValue"] = -100
    rows = metrics(service.build_valuation("AAPL", fundamentals, info, now=NOW))
    assert rows["ev_ebitda"]["value"] is None
    assert rows["ev_ebitda"]["status"] == "unavailable"
    assert rows["ev_sales"]["value"] == -0.1


def test_nonfinite_booleans_and_zero_market_cap_are_not_valid_ratio_inputs():
    fundamentals, info = observations()
    fundamentals["ttm"].update(revenue_ttm=float("nan"), fcf_ttm=False, operating_margin_ttm=float("inf"))
    info["marketCap"] = 0
    result = service.build_valuation("AAPL", fundamentals, info, now=NOW)
    rows = metrics(result)
    assert rows["ev_sales"]["value"] is None
    assert rows["fcf_yield"]["value"] is None
    assert rows["operating_margin"]["value"] is None
    assert result["financials"]["fcf_ttm"] is None


def test_auth_validation_and_partial_data_route(monkeypatch):
    calls = []

    async def read(symbol):
        calls.append(symbol)
        return service.build_valuation(symbol, {}, {}, now=NOW)

    monkeypatch.setattr(router, "get_valuation", read)
    app = FastAPI()
    app.include_router(router.router, prefix="/api/valuation")

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
            assert (await client.get("/api/valuation/AAPL")).status_code == 401
            assert not calls
            app.dependency_overrides[verify_password_with_role] = lambda: "guest"
            assert (await client.get("/api/valuation/!invalid")).status_code == 422
            response = await client.get("/api/valuation/brk.b")
            assert response.status_code == 200
            assert response.json()["symbol"] == "BRK-B"
            assert len(response.json()["valuation"]) == 3
            assert all(row["value"] is None for row in response.json()["valuation"])

    asyncio.run(exercise())
    assert calls == ["BRK-B"]


def test_provider_jobs_stay_bounded_after_request_timeout_and_same_symbol_shares_work(monkeypatch):
    release = Event()
    started = Event()
    guard = Lock()
    calls = []

    def load(symbol):
        with guard:
            calls.append(symbol)
            if len(calls) == 4:
                started.set()
        assert release.wait(3)
        return {"symbol": symbol}

    with ThreadPoolExecutor(max_workers=4) as pool:
        monkeypatch.setattr(service, "_pool", pool)
        monkeypatch.setattr(service, "_cache", TTLCache(maxsize=100, ttl=90))
        monkeypatch.setattr(service, "_inflight", {})
        monkeypatch.setattr(service, "_load", load)
        monkeypatch.setattr(service, "REQUEST_TIMEOUT_SECONDS", 0.05)

        async def exercise():
            tasks = [asyncio.create_task(service.get_valuation(symbol)) for symbol in ("AAA", "BBB", "CCC", "DDD", "AAA")]
            try:
                assert await asyncio.to_thread(started.wait, 1)
                results = await asyncio.gather(*tasks, return_exceptions=True)
                assert all(isinstance(item, asyncio.TimeoutError) for item in results)
                assert len(service._inflight) == 4
                with pytest.raises(service.ValuationBusy):
                    await service.get_valuation("EEE")
                assert calls.count("AAA") == 1
            finally:
                release.set()
                await asyncio.gather(*(asyncio.wrap_future(future) for future in list(service._inflight.values())))
            assert await service.get_valuation("AAA") == {"symbol": "AAA"}
            assert len(calls) == 4
            assert not service._inflight

        asyncio.run(exercise())
