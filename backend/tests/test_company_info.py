"""Offline regression coverage for company metrics and their observation times."""

import importlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest
import backend.core.market_provider as yf


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
        "trailingAnnualDividendYield": 0, "beta": 0, "trailingEps": -1.25,
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


def test_incomplete_latest_history_uses_last_observed_close_and_its_date(api, monkeypatch):
    history = pd.DataFrame({"Close": [10, float("nan")]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"], utc=True))
    fake_ticker(monkeypatch, {"regularMarketTime": float("inf")}, history)
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["lastTradePrice"] == 10
    assert data["history_as_of"] == "2020-01-01T00:00:00+00:00"
    for key in ("quote_as_of", "lastTradeChange", "lastTradeChangePercent"):
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


def test_trailing_yield_uses_annual_dividends_and_the_displayed_quote(api, monkeypatch):
    fake_ticker(monkeypatch, {
        "currentPrice": 340, "regularMarketPrice": 300, "dividendYield": .31,
        "trailingAnnualDividendRate": 1.04, "trailingAnnualDividendYield": .0035,
    })
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["dividendYield"] == pytest.approx(1.04 / 340)
    assert data["dividendYieldBasis"] == "trailing_annual_rate_over_quote"
    assert data["dividendYield"] * 100 == pytest.approx(.30588235)


def test_trailing_yield_uses_the_quote_fallback_and_preserves_observed_zero(api, monkeypatch):
    fake_ticker(monkeypatch, {
        "currentPrice": None, "regularMarketPrice": 42,
        "trailingAnnualDividendRate": 0, "dividendYield": 1.5,
    })
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["currentPrice"] == 42
    assert data["dividendYield"] == 0
    assert data["dividendYieldBasis"] == "trailing_annual_rate_over_quote"


@pytest.mark.parametrize("value", [0, .0031, 1.5])
def test_explicit_trailing_yield_remains_decimal_without_magnitude_guessing(api, monkeypatch, value):
    fake_ticker(monkeypatch, {"trailingAnnualDividendYield": value, "dividendYield": .31})
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["dividendYield"] == value
    assert data["dividendYieldBasis"] == "provider_trailing_annual"


@pytest.mark.parametrize("info", [
    {"dividendYield": .31},
    {"dividendYield": 0},
    {"trailingAnnualDividendRate": 1, "currentPrice": 0},
    {"trailingAnnualDividendRate": 1, "currentPrice": -10},
    {"trailingAnnualDividendRate": -1, "currentPrice": 42},
    {"trailingAnnualDividendYield": float("nan")},
    {"trailingAnnualDividendYield": float("inf")},
    {"trailingAnnualDividendYield": -1},
    {"trailingAnnualDividendYield": False},
])
def test_unavailable_or_invalid_dividend_inputs_stay_unavailable(api, monkeypatch, info):
    fake_ticker(monkeypatch, info)
    success, data = api.get_company_info("AAPL")
    assert success
    assert data["dividendYield"] is None
    assert data["dividendYieldBasis"] is None
    json.dumps(data, allow_nan=False)


def test_yahoo_budget_denial_is_429_without_contacting_provider(api, monkeypatch):
    from backend.core import resources
    resources.reserve('yahoo', cooldown=0)
    monkeypatch.setenv('PROVIDER_YAHOO_DAILY_LIMIT', '1')
    monkeypatch.setattr(yf, 'Ticker', lambda *args: pytest.fail('Budget denial must happen before the SDK'))
    for request in [api.get_company_info_endpoint, api.get_price_history]:
        with pytest.raises(api.HTTPException) as error:
            request('IBM', current_user='admin')
        assert error.value.status_code == 429
        assert 'daily limit reached (1/1)' in error.value.detail
        assert 0 < int(error.value.headers['Retry-After']) <= 86400
    # Cached observations remain accessible after the limit, without new requests.
    from backend.core.provider_cache import fetch_snapshot
    frame = pd.DataFrame({'Open': [42.], 'High': [42.], 'Low': [42.], 'Close': [42.], 'Volume': [0.]},
                         index=pd.date_range('2024-01-01', periods=1, tz='UTC'))
    fetch_snapshot('yahoo-history-v1', ['MSFT', {'period': '1y', 'interval': '1d'}, False],
                   lambda: {'frame': frame.to_json(orient='table', date_format='iso'), 'metadata': {}})
    result = api.get_price_history('MSFT', current_user='admin')
    assert result['lastHistoricalCloseDate'] == '2024-01-01'
    assert result['lastHistoricalClose'] == 42


def test_swallowed_sdk_budget_error_is_not_reported_as_missing_history(api, monkeypatch):
    from backend.core.resources import reserve
    monkeypatch.setenv('PROVIDER_YAHOO_DAILY_LIMIT', '1')
    def swallowed(**kwargs):
        reserve('yahoo', cooldown=0)
        return pd.DataFrame()
    monkeypatch.setattr(yf, 'Ticker', lambda symbol: SimpleNamespace(history=swallowed))
    with pytest.raises(api.HTTPException) as error:
        api.get_price_history('IBM', current_user='admin')
    assert error.value.status_code == 429


def test_chart_and_metrics_share_profile_and_do_not_fetch_extra_five_day_history(api, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import time
    calls = {'info': 0, 'history': []}
    class Ticker:
        @property
        def info(self):
            calls['info'] += 1
            time.sleep(.03)
            return {'symbol': 'IBM', 'currentPrice': 42, 'regularMarketTime': 1704240000}
        def history(self, **kwargs):
            calls['history'].append(kwargs)
            return pd.DataFrame({'Open': [40.], 'High': [43.], 'Low': [39.], 'Close': [42.], 'Volume': [0.]},
                                index=pd.date_range('2024-01-02', periods=1, tz='America/New_York'))
    monkeypatch.setattr(yf, 'Ticker', lambda _: Ticker())
    with ThreadPoolExecutor(max_workers=2) as pool:
        quote = pool.submit(api.get_company_info_endpoint, 'IBM', 'admin')
        chart = pool.submit(api.get_price_history, 'IBM', current_user='admin')
        assert quote.result()['currentPrice'] == chart.result()['currentPrice'] == 42
    assert calls['info'] == 1
    assert len(calls['history']) == 1
    assert calls['history'][0]['period'] == '1y'
    # Restart drops the API's in-memory cache; durable observations still serve both.
    api.cache.invalidate()
    monkeypatch.setattr(yf, 'Ticker', lambda _: pytest.fail('Restart must not contact Yahoo'))
    assert api.get_company_info_endpoint('IBM', 'admin')['currentPrice'] == 42
    assert api.get_price_history('IBM', current_user='admin')['data'][0]['volume'] == 0


@pytest.mark.parametrize('period, interval', [('garbage', '1d'), ('1y', '1m'), ('max', '1d')])
def test_chart_rejects_unbounded_query_variants_before_provider(api, monkeypatch, period, interval):
    monkeypatch.setattr(yf, 'Ticker', lambda _: pytest.fail('Invalid ranges must not contact Yahoo'))
    with pytest.raises(api.HTTPException) as error:
        api.get_price_history('IBM', period=period, interval=interval, current_user='admin')
    assert error.value.status_code == 422
