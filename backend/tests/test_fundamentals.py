"""Tests for fundamentals analytics backend."""

from unittest.mock import Mock, patch

import pandas as pd

from backend.models.fundamentals import FundamentalsSeries, FundamentalsTTM
from backend.services.fundamentals import (
    FundamentalsService,
    compute_quarterly_series,
    compute_ttm_metrics,
)


def _dt_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame columns to datetime to mirror yfinance output."""
    df.columns = pd.to_datetime(df.columns)
    return df


def _mock_ticker_with_financials(mock_ticker):
    """Attach realistic quarterly/annual financial data to yfinance.Ticker mock."""
    quarterly_financials = _dt_cols(
        pd.DataFrame(
            {
                "2023-12-31": [1_000_000, 200_000, 300_000],
                "2023-09-30": [950_000, 180_000, 280_000],
                "2023-06-30": [900_000, 160_000, 260_000],
                "2023-03-31": [850_000, 140_000, 240_000],
            },
            index=["Total Revenue", "Operating Income", "EBITDA"],
        )
    )

    quarterly_cashflow = _dt_cols(
        pd.DataFrame(
            {
                "2023-12-31": [150_000, -50_000],
                "2023-09-30": [140_000, -45_000],
                "2023-06-30": [130_000, -40_000],
                "2023-03-31": [120_000, -35_000],
            },
            index=["Operating Cash Flow", "Capital Expenditures"],
        )
    )

    quarterly_balance_sheet = _dt_cols(
        pd.DataFrame(
            {
                "2023-12-31": [500_000, 200_000],
                "2023-09-30": [490_000, 195_000],
            },
            index=["Total Debt", "Cash And Cash Equivalents"],
        )
    )

    annual_financials = _dt_cols(
        pd.DataFrame(
            {
                "2023-12-31": [3_700_000, 720_000],
                "2022-12-31": [3_300_000, 640_000],
            },
            index=["Total Revenue", "Operating Income"],
        )
    )

    annual_cashflow = _dt_cols(
        pd.DataFrame(
            {
                "2023-12-31": [540_000, -170_000],
                "2022-12-31": [500_000, -160_000],
            },
            index=["Operating Cash Flow", "Capital Expenditures"],
        )
    )

    mock_ticker_instance = Mock()
    mock_ticker_instance.quarterly_financials = quarterly_financials
    mock_ticker_instance.quarterly_cashflow = quarterly_cashflow
    mock_ticker_instance.quarterly_balance_sheet = quarterly_balance_sheet
    mock_ticker_instance.financials = annual_financials
    mock_ticker_instance.cashflow = annual_cashflow
    mock_ticker.return_value = mock_ticker_instance


def test_fundamentals_service_initialization():
    service = FundamentalsService()
    assert service is not None


@patch("yfinance.Ticker")
def test_compute_ttm_metrics_with_mock_data(mock_ticker):
    _mock_ticker_with_financials(mock_ticker)

    result = compute_ttm_metrics("TEST")

    assert isinstance(result, FundamentalsTTM)
    assert result.ticker == "TEST"
    assert result.insufficient_data is False
    assert result.revenue_ttm is not None
    assert result.operating_income_ttm is not None
    assert result.fcf_ttm is not None


@patch("yfinance.Ticker")
def test_compute_quarterly_series_with_mock_data(mock_ticker):
    _mock_ticker_with_financials(mock_ticker)

    result = compute_quarterly_series("TEST")

    assert isinstance(result, FundamentalsSeries)
    assert result.revenue_q is not None
    assert len(result.revenue_q) == 4
    assert result.operating_income_q is not None
    assert result.fcf_q is not None


@patch("yfinance.Ticker")
def test_fundamentals_service_wrapper_response(mock_ticker):
    _mock_ticker_with_financials(mock_ticker)

    service = FundamentalsService()
    payload = service.get_fundamentals_data("TEST")

    assert payload["ticker"] == "TEST"
    assert "ttm" in payload
    assert "series" in payload
    assert "metadata" in payload
    assert payload["metadata"]["insufficient_data"] is False