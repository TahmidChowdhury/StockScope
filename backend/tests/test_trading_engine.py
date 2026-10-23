"""Hand-computed accounting and information-timing checks; no network."""
import copy
from datetime import date

import pytest

from backend.trading.engine import simulate
from backend.trading.models import BacktestInput, Costs


def bars(prices, days=None):
    days = days or [f"2025-01-{day:02d}" for day in range(2, len(prices) + 2)]
    return [{"date": d, "open": p, "close": p, "split": 1, "dividend": 0} for d, p in zip(days, prices)]


def run(data=None, signals=None, costs=None, strategy="orders", **kwargs):
    return simulate(data=data or {"AAPL": bars([10, 12, 11]), "SPY": bars([10, 11, 12])},
                    start="2025-01-02", end="2025-01-04", initial_cash=1000, benchmark="SPY",
                    symbols=["AAPL"], costs=costs or Costs(slippage_bps=0, spread_bps=0, commission=0),
                    signals=signals, strategy=strategy, **kwargs)


def signal(side, day, **extra):
    return {"id": day + side, "side": side, "symbol": "AAPL", "signal_date": day, "budget": 1000, **extra}


def test_cash_and_realized_pnl_include_both_sides_of_costs():
    costs = Costs(slippage_bps=100, spread_bps=200, commission=1)
    result = run(signals=[signal("buy", "2025-01-01"), signal("sell", "2025-01-02")], costs=costs)
    shares = 999 / 10.2
    cash = shares * 11.76 - 1
    assert result["cash"] == pytest.approx(cash)
    assert result["metrics"]["realized_pnl"] == pytest.approx(cash - 1000)
    assert result["metrics"]["total_costs"] == pytest.approx(shares * (0.2 + 0.24) + 2)
    assert result["metrics"]["total_return"] == pytest.approx(cash / 1000 - 1)
    assert result["positions"] == []


def test_disclosure_delay_does_not_get_original_or_same_day_price():
    result = run(signals=[signal("buy", "2025-01-02", transaction_date="2024-12-01")])
    assert result["fills"][0]["execution_date"] == "2025-01-03"
    assert result["fills"][0]["price"] == 12
    assert result["curve"][0]["equity"] == 1000
    assert result["metrics"]["total_return"] == pytest.approx(11 / 12 - 1)


def test_end_day_disclosure_stays_pending_and_does_not_change_return():
    result = run(signals=[signal("buy", "2025-01-04")])
    assert len(result["pending"]) == 1
    assert not result["fills"]
    assert result["metrics"]["total_return"] == 0


def test_weekend_disclosure_uses_next_observed_session():
    days = ["2025-01-03", "2025-01-06", "2025-01-07"]
    data = {"AAPL": bars([10, 20, 30], days), "SPY": bars([10, 10, 10], days)}
    result = simulate(data=data, start=days[0], end=days[-1], initial_cash=1000, benchmark="SPY", symbols=["AAPL"], costs=Costs(), signals=[signal("buy", "2025-01-04")])
    assert result["fills"][0]["execution_date"] == "2025-01-06"


def test_splits_and_cash_dividends_preserve_economic_value_and_basis():
    data = {"AAPL": bars([100, 50, 49]), "SPY": bars([10, 10, 10])}
    data["AAPL"][1]["split"] = 2
    data["AAPL"][2]["dividend"] = 1
    result = run(data=data, signals=[signal("buy", "2025-01-01")])
    position = result["positions"][0]
    assert position["shares"] == 20
    assert position["cost_basis"] == 1000
    assert result["cash"] == 20
    assert result["metrics"]["dividends"] == 20
    assert result["metrics"]["total_return"] == 0
    assert result["metrics"]["max_drawdown"] == 0


def test_buy_on_ex_date_does_not_receive_prior_holders_dividend():
    data = {"AAPL": bars([10, 9, 9]), "SPY": bars([10, 10, 10])}
    data["AAPL"][1]["dividend"] = 1
    result = run(data=data, signals=[signal("buy", "2025-01-02")])
    assert result["metrics"]["dividends"] == 0


def test_missing_stock_history_stops_instead_of_dropping_losing_stock():
    data = {"AAPL": bars([10, 12, 11]), "SPY": bars([10, 11, 12])}
    del data["AAPL"][1]
    with pytest.raises(ValueError, match="AAPL has missing daily data"):
        run(data=data)


def test_cash_caps_buys_and_prevents_short_sales():
    result = run(signals=[signal("sell", "2025-01-01"), signal("buy", "2025-01-02", budget=1000000)])
    assert len(result["rejected"]) == 1
    assert result["cash"] == pytest.approx(0)
    assert result["positions"][0]["shares"] == pytest.approx(1000 / 12)


def test_position_cap_applies_to_repeated_disclosures():
    result = run(signals=[signal("buy", "2025-01-01", max_weight=.25), signal("buy", "2025-01-01", max_weight=.25)])
    assert result["fills"][0]["shares"] == 25
    assert len(result["fills"]) == 1
    assert result["rejected"][0]["reason"] == "Insufficient cash or position limit"


def test_identical_strategy_and_benchmark_have_zero_excess_return():
    prices = bars([10, 12, 11])
    result = run(data={"AAPL": prices, "SPY": copy.deepcopy(prices)}, strategy="buy_hold", costs=Costs(commission=2))
    assert result["metrics"]["excess_return"] == 0
    assert result["metrics"]["total_costs"] == result["metrics"]["benchmark_costs"]
    assert result["metrics"]["max_drawdown"] == pytest.approx(11 / 12 - 1)
    assert result["metrics"]["cagr"] is None


def test_sma_uses_prior_close_and_future_prices_cannot_change_earlier_fills():
    dates = ["2024-12-29", "2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03", "2025-01-04"]
    data = {"AAPL": bars([10, 11, 12, 13, 1, 2], dates), "SPY": bars([10] * 6, dates)}
    first = run(data=data, strategy="sma", fast_window=2, slow_window=3)
    assert first["fills"][0]["side"] == "buy"
    assert first["fills"][0]["execution_date"] == "2025-01-02"
    assert first["fills"][1]["side"] == "sell"
    assert first["fills"][1]["execution_date"] == "2025-01-04"
    data["AAPL"][-1]["close"] = 99999
    second = run(data=data, strategy="sma", fast_window=2, slow_window=3)
    assert first["fills"] == second["fills"]


def test_sma_adjusts_split_before_calculating_indicator():
    dates = ["2024-12-29", "2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03", "2025-01-04"]
    data = {"AAPL": bars([100, 110, 120, 65, 70, 75], dates), "SPY": bars([10] * 6, dates)}
    data["AAPL"][3]["split"] = 2
    result = run(data=data, strategy="sma", fast_window=2, slow_window=3)
    assert [f["side"] for f in result["fills"]] == ["buy"]


def test_sma_requires_real_warmup():
    with pytest.raises(ValueError, match="pre-start history"):
        run(strategy="sma")


@pytest.mark.parametrize("change", [{"name": "x" * 81}, {"initial_cash": float('nan')}, {"symbols": []}, {"end": "2025-01-01"}, {"fast_window": 50}, {"strategy": "congress", "member": " "}, {"strategy": "sma", "symbols": ["AAPL", "MSFT"]}, {"benchmark": "../../bad"}, {"costs": {"commission": float('inf')}}])
def test_backtest_input_rejects_invalid_financial_assumptions(change):
    with pytest.raises(ValueError):
        BacktestInput.model_validate({"start": "2025-01-01", "end": "2025-12-31", **change})
