"""Offline regression coverage for company metrics and their observation times."""

import importlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest
import yfinance as yf


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "fixture-admin")
    monkeypatch.setenv("DEMO_PASSWORD", "fixture-demo")
    monkeypatch.setenv("GUEST_PASSWORD", "fixture-guest")
    monkeypatch.setenv("STOCKSCOPE_PASSWORD", "fixture-admin")
    monkeypatch.setenv("SECRET_KEY", "fixture-signing-key-not-a-password-1234567890")
    module = importlib.import_module("backend.api")
    module.cache.invalidate()
    yield module
    module.cache.invalidate()


def fake_ticker(monkeypatch, info, history=None):
    ticker = SimpleNamespace(
        info=info,
        history=lambda **kwargs: history if history is not None else pd.DataFrame(),
    )
    monkeypatch.setattr(yf, "Ticker", lambda symbol: ticker)
    return ticker


def test_missing_and_nonfinite_metrics_are_unavailable_but_observed_zero_survives(api, monkeypatch):
    fake_ticker(monkeypatch, {
        "volume": None, "marketCap": float("nan"), "dayHigh": float("inf"),
        "dayLow": False, "averageVolume": 0, "trailingPE": 0,
        "dividendYield": 0, "beta": 0, "trailingEps": -1.25,
    })
    success, data = api.get_company_info("aapl")
    assert success
    assert data["symbol"] == data["displayName"] == "AAPL"
    for key in ("volume", "marketCap", "dayHigh", "dayLow", "currentPrice", "priceToBook"):
        assert data[key] is None
    for key in ("averageVolume", "priceToEarningsRatio", "dividendYield", "beta"):
        assert data[key] == 0
    assert data["earningsPerShare"] == -1.25
    assert data["currency"] is None
    assert data["quote_as_of"] is None
    json.dumps(data, allow_nan=False)


@pytest.mark.parametrize("current, expected", [(None, 42.0), (float("nan"), 42.0), (0, 0.0)])
def test_price_fallback_uses_an_observed_value_without_erasing_zero(api, monkeypatch, current, expected):
    fake_ticker(monkeypatch, {"currentPrice": current, "regularMarketPrice": 42})
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["currentPrice"] == expected


def test_cached_response_retains_quote_and_retrieval_times(api, monkeypatch):
    ticker = fake_ticker(monkeypatch, {"regularMarketTime": 1609459200, "currentPrice": 42})
    before = datetime.now(timezone.utc)
    first = api.get_company_info_endpoint("AAPL", "demo")
    after = datetime.now(timezone.utc)
    assert first["quote_as_of"] == "2021-01-01T00:00:00+00:00"
    assert before <= datetime.fromisoformat(first["retrieved_at"]) <= after
    ticker.info = {"regularMarketTime": 1640995200, "currentPrice": 100}
    second = api.get_company_info_endpoint("AAPL", "demo")
    assert second == first
    assert second["currentPrice"] == 42
    assert second["quote_as_of"] != second["retrieved_at"]


def test_history_does_not_supply_a_quote_time_or_divide_by_zero(api, monkeypatch):
    history = pd.DataFrame({"Close": [0, 10]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"], utc=True))
    fake_ticker(monkeypatch, {}, history)
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["currentPrice"] is None
    assert data["quote_as_of"] is None
    assert data["history_as_of"] == "2020-01-02T00:00:00+00:00"
    assert data["lastTradePrice"] == 10
    assert data["lastTradeChange"] == 10
    assert data["lastTradeChangePercent"] is None
    json.dumps(data, allow_nan=False)


def test_nonfinite_history_stays_unavailable(api, monkeypatch):
    history = pd.DataFrame({"Close": [10, float("nan")]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"], utc=True))
    fake_ticker(monkeypatch, {"regularMarketTime": float("inf")}, history)
    success, data = api.get_company_info("AAPL")
    assert success
    for key in ("quote_as_of", "lastTradePrice", "lastTradeChange", "lastTradeChangePercent"):
        assert data[key] is None
    json.dumps(data, allow_nan=False)


def test_history_failure_does_not_discard_observed_metrics(api, monkeypatch):
    ticker = fake_ticker(monkeypatch, {"volume": 0, "currentPrice": 42})

    def failed_history(**kwargs):
        raise RuntimeError("fixture provider unavailable")

    ticker.history = failed_history
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["volume"] == 0
    assert data["currentPrice"] == 42
    assert data["lastTradePrice"] is None
