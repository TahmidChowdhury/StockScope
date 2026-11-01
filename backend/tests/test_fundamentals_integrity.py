"""Deterministic financial examples: no provider calls or fabricated market data."""

import asyncio
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from backend.models.fundamentals import ScreenerRequest
from backend.routers.fundamentals import screen_fundamentals
from backend.services.fundamentals import (
    _ttm, compute_quarterly_series, compute_ttm_metrics, fetch_annuals, fetch_quarterlies,
)


def series(values, dates=None):
    return pd.Series(values, index=pd.to_datetime(dates) if dates is not None else pd.date_range("2023-03-31", periods=len(values), freq="QE"), dtype=float)


def quarterly(**overrides):
    data = {
        "revenue": series([100] * 8), "op_inc": series([10] * 8),
        "fcf": series([5] * 8), "ebitda": series([15] * 8),
        "debt": series([0] * 8), "cash_and_sti": series([20] * 8),
    }
    data.update(overrides)
    return data


def calculate(**overrides):
    return compute_ttm_metrics("TEST", quarterlies=quarterly(**overrides), annuals={})


def mock_provider(income, cashflow, balance=None):
    dates = pd.date_range("2024-03-31", periods=4, freq="QE")
    ticker = Mock()
    ticker.quarterly_financials = pd.DataFrame(income, index=dates).T
    ticker.quarterly_cashflow = pd.DataFrame(cashflow, index=dates).T
    ticker.quarterly_balance_sheet = pd.DataFrame(balance or {}, index=dates).T
    ticker.financials = ticker.quarterly_financials
    ticker.cashflow = ticker.quarterly_cashflow
    return patch("backend.services.fundamentals.yf.Ticker", return_value=ticker)


def test_hand_calculated_totals_and_margins_preserve_zero_debt():
    result = calculate(revenue=series([100] * 4 + [125] * 4), op_inc=series([10] * 4 + [25] * 4))
    assert result.revenue_ttm == 500
    assert result.operating_income_ttm == 100
    assert result.operating_margin_ttm == pytest.approx(.20)
    assert result.revenue_growth_yoy == pytest.approx(.25)
    assert result.margin_growth_yoy_pp == pytest.approx(10)
    assert result.total_debt == 0
    assert result.debt_to_cash == 0
    assert result.net_debt == -20
    expected_period = quarterly()["debt"].index[-1].date().isoformat()
    for field in ("total_debt", "cash_and_equivalents", "net_debt", "debt_to_cash"):
        assert result.period_metadata[field] == {"basis": "balance_sheet", "period_end": expected_period}


def test_missing_capex_is_unknown_fcf_in_both_quarterly_and_annual_paths():
    with mock_provider({"Total Revenue": [100] * 4}, {"Operating Cash Flow": [80] * 4}):
        assert fetch_quarterlies("TEST")["fcf"].empty
        assert fetch_annuals("TEST")["fcf"].empty


@pytest.mark.parametrize("capex,expected", [(-30, 50), (30, 50), (0, 80)])
def test_fcf_uses_capex_outflow_and_accepts_reported_zero(capex, expected):
    with mock_provider({}, {"Operating Cash Flow": [80] * 4, "Capital Expenditure": [capex] * 4}):
        assert _ttm(fetch_quarterlies("TEST")["fcf"]) == expected * 4


def test_investments_is_not_a_capex_alias():
    with mock_provider({}, {"Operating Cash Flow": [80] * 4, "Investments": [-30] * 4}):
        assert fetch_quarterlies("TEST")["fcf"].empty


def test_ebitda_rejects_ambiguous_aliases_and_incomplete_components():
    income = {"Net Income": [100] * 4, "Pretax Income": [125] * 4, "Net Interest Income": [20] * 4,
              "Operating Income": [90] * 4, "NormalizedEBITDA": [180] * 4}
    with mock_provider(income, {"Depreciation And Amortization": [5] * 4}):
        assert fetch_quarterlies("TEST")["ebitda"].empty


def test_ebitda_complete_derivation_preserves_tax_benefits():
    income = {"Net Income": [100] * 4, "Interest Expense": [10] * 4, "Tax Provision": [-5] * 4}
    with mock_provider(income, {"Depreciation And Amortization": [20] * 4}):
        assert _ttm(fetch_quarterlies("TEST")["ebitda"]) == 500


def test_ebitda_can_use_ebit_and_total_da():
    with mock_provider({"EBIT": [100] * 4}, {"Depreciation And Amortization": [20] * 4}):
        assert _ttm(fetch_quarterlies("TEST")["ebitda"]) == 480


@pytest.mark.parametrize("values,dates", [
    ([100] * 4, ["2023-03-31", "2023-06-30", "2023-09-30", "2026-06-30"]),
    ([100, float("nan"), 100, 100], None),
    ([100, float("inf"), 100, 100], None),
    ([100] * 4, ["2023-03-31", "2023-06-30", "2023-06-30", "2023-09-30"]),
])
def test_ttm_rejects_missing_nonfinite_or_duplicate_quarters(values, dates):
    assert _ttm(series(values, dates)) is None


def test_53_week_fiscal_calendar_is_supported():
    assert _ttm(series([100] * 4, ["2023-04-01", "2023-07-01", "2023-09-30", "2024-01-06"])) == 400


def test_three_quarters_is_insufficient_and_stale_components_do_not_create_margin():
    assert calculate(revenue=series([100] * 3)).insufficient_data
    result = calculate(op_inc=series([10] * 7))
    assert result.operating_income_ttm is None
    assert result.operating_margin_ttm is None
    assert result.insufficient_data


def test_margin_requires_identical_quarter_periods():
    income = series([10] * 8)
    income.index = pd.DatetimeIndex([income.index[0] - pd.Timedelta(days=1), *income.index[1:]])
    result = calculate(op_inc=income)
    assert result.margin_growth_yoy_pp is None


@pytest.mark.parametrize("prior,current", [(-100, -50), (0, 50)])
def test_nonpositive_prior_fcf_is_not_misrepresented_as_percentage_growth(prior, current):
    result = compute_ttm_metrics("TEST", quarterlies=quarterly(fcf=series([prior] * 4 + [current] * 4)),
                                 annuals={"fcf": series([100, 200], ["2022-12-31", "2023-12-31"])})
    assert result.fcf_growth_yoy is None
    assert result.growth_metadata["fcf_growth_yoy"] == {
        "basis": "ttm", "status": "non_positive_prior", "current_period_end": "2024-12-31",
        "prior_period_end": "2023-12-31", "absolute_change": 200,
    }


def test_zero_ttm_growth_does_not_trigger_annual_fallback():
    result = compute_ttm_metrics("TEST", quarterlies=quarterly(),
                                 annuals={"revenue": series([100, 200], ["2022-12-31", "2023-12-31"])})
    assert result.revenue_growth_yoy == 0
    assert result.growth_metadata["revenue_growth_yoy"]["basis"] == "ttm"


def test_annual_fallback_identifies_periods_and_basis():
    result = compute_ttm_metrics("TEST", quarterlies=quarterly(revenue=series([100] * 4)),
                                 annuals={"revenue": series([200, 300], ["2022-12-31", "2023-12-31"])})
    assert result.revenue_growth_yoy == .5
    assert result.growth_metadata["revenue_growth_yoy"]["basis"] == "fiscal_year"
    assert result.growth_metadata["revenue_growth_yoy"]["current_period_end"] == "2023-12-31"


def test_quarterly_series_keeps_zero_income_and_fcf_and_chronological_dates():
    result = compute_quarterly_series("TEST", quarterlies=quarterly(op_inc=series([0] * 8), fcf=series([0] * 8)))
    assert [point.value for point in result.operating_margin_q] == [0] * 8
    assert [point.value for point in result.fcf_margin_q] == [0] * 8
    assert [point.date for point in result.revenue_q] == sorted(point.date for point in result.revenue_q)


def test_aggregate_cash_is_not_double_counted_with_short_term_investments():
    with mock_provider({}, {}, {"CashAndShortTermInvestments": [100] * 4, "Short Term Investments": [25] * 4}):
        assert fetch_quarterlies("TEST")["cash_and_sti"].iloc[-1] == 100


def screen(request, rows):
    with patch("backend.routers.fundamentals.peek_many", return_value={symbol: {"ttm": row} for symbol, row in rows.items() if row is not None}):
        return asyncio.run(screen_fundamentals(request, current_user="member"))


def test_screener_counts_all_matches_before_limit_and_reports_partial_coverage():
    rows = {
        "A": {"ticker": "A", "insufficient_data": False, "revenue_growth_yoy": .1},
        "B": {"ticker": "B", "insufficient_data": False, "revenue_growth_yoy": .2},
        "C": None, "D": {"ticker": "D", "insufficient_data": True},
    }
    result = screen(ScreenerRequest(universe=["a", "A", "B", "C", "D"], limit=1), rows)
    assert result.total_attempted == 4
    assert result.total_failed == 1
    assert result.total_insufficient == 1
    assert result.total_evaluated == 2
    assert result.total_matches == 2
    assert len(result.results) == 1
    assert result.results[0]["ticker"] == "B"
    assert result.universe_name == "Custom stock list"


def test_screener_percentage_points_and_zero_filters():
    rows = {
        "A": {"ticker": "A", "insufficient_data": False, "margin_growth_yoy_pp": .5, "debt_to_cash": 0},
        "B": {"ticker": "B", "insufficient_data": False, "margin_growth_yoy_pp": 1.5, "debt_to_cash": 0},
        "C": {"ticker": "C", "insufficient_data": False, "margin_growth_yoy_pp": 2, "debt_to_cash": 1},
    }
    result = screen(ScreenerRequest(universe=list(rows), min_margin_growth_yoy_pp=1, max_debt_to_cash=0), rows)
    assert [row["ticker"] for row in result.results] == ["B"]


def test_screener_unknown_growth_never_passes_filter_and_sorts_last():
    rows = {
        "A": {"ticker": "A", "insufficient_data": False, "revenue_growth_yoy": 0},
        "B": {"ticker": "B", "insufficient_data": False},
    }
    filtered = screen(ScreenerRequest(universe=list(rows), min_revenue_growth_yoy=0), rows)
    assert [row["ticker"] for row in filtered.results] == ["A"]
    sorted_rows = screen(ScreenerRequest(universe=list(rows), sort_dir="asc"), rows)
    assert [row["ticker"] for row in sorted_rows.results] == ["A", "B"]


def test_screen_preserves_each_reporting_currency_in_saved_results():
    rows = {symbol: {'ticker': symbol, 'insufficient_data': False, 'revenue_ttm': 100,
                     'reporting_currency': unit}
            for symbol, unit in [('A', 'EUR'), ('B', 'JPY'), ('C', None)]}
    result = screen(ScreenerRequest(universe=list(rows)), rows)
    assert {row['ticker']: row.get('reporting_currency') for row in result.results} == {'A': 'EUR', 'B': 'JPY', 'C': None}
