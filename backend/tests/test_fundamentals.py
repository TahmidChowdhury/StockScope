"""Tests for fundamentals analytics backend."""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch
import numpy as np

from backend.services.fundamentals import (
    FundamentalsService,
    compute_ttm_metrics,
    compute_quarterly_series
)
from backend.models.fundamentals import (
    FundamentalsTTM,
    FundamentalsSeries,
    FundamentalPoint
)


def test_fundamentals_service_initialization():
    """Test that FundamentalsService can be initialized without DatetimeIndex errors."""
    service = FundamentalsService()
    assert service is not None


@patch('yfinance.Ticker')
def test_compute_ttm_metrics_with_mock_data(mock_ticker):
    """Test TTM metrics computation with mocked data to avoid DatetimeIndex comparison errors."""
    # Create mock data that mimics yfinance structure
    mock_income_data = pd.DataFrame({
        '2023-12-31': [1000000, 200000, 300000],
        '2023-09-30': [950000, 180000, 280000],
        '2023-06-30': [900000, 160000, 260000], 
        '2023-03-31': [850000, 140000, 240000]
    }, index=['Total Revenue', 'Operating Income', 'EBITDA'])
    
    mock_cashflow_data = pd.DataFrame({
        '2023-12-31': [150000, -50000],
        '2023-09-30': [140000, -45000],
        '2023-06-30': [130000, -40000],
        '2023-03-31': [120000, -35000]
    }, index=['Operating Cash Flow', 'Capital Expenditures'])
    
    mock_balance_data = pd.DataFrame({
        '2023-12-31': [500000, 200000]
    }, index=['Total Debt', 'Cash And Cash Equivalents'])
    
    # Convert column names to DatetimeIndex to match yfinance format
    mock_income_data.columns = pd.to_datetime(mock_income_data.columns)
    mock_cashflow_data.columns = pd.to_datetime(mock_cashflow_data.columns)
    mock_balance_data.columns = pd.to_datetime(mock_balance_data.columns)
    
    # Mock the yfinance ticker object
    mock_ticker_instance = Mock()
    mock_ticker_instance.quarterly_income_stmt = mock_income_data
    mock_ticker_instance.quarterly_cashflow = mock_cashflow_data
    mock_ticker_instance.quarterly_balance_sheet = mock_balance_data
    mock_ticker.return_value = mock_ticker_instance
    
    # This should not raise a DatetimeIndex comparison error
    result = compute_ttm_metrics('TEST')
    
    assert isinstance(result, FundamentalsTTM)
    assert result.ticker == 'TEST'
    # Should not have insufficient data with 4 quarters
    assert result.insufficient_data is False


@patch('yfinance.Ticker') 
def test_compute_quarterly_series_with_mock_data(mock_ticker):
    """Test quarterly series computation with mocked data."""
    # Create mock data
    mock_income_data = pd.DataFrame({
        '2023-12-31': [1000000, 200000],
        '2023-09-30': [950000, 180000],
        '2023-06-30': [900000, 160000], 
        '2023-03-31': [850000, 140000]
    }, index=['Total Revenue', 'Operating Income'])
    
    mock_cashflow_data = pd.DataFrame({
        '2023-12-31': [150000, -50000],
        '2023-09-30': [140000, -45000],
        '2023-06-30': [130000, -40000],
        '2023-03-31': [120000, -35000]
    }, index=['Operating Cash Flow', 'Capital Expenditures'])
    
    # Convert to DatetimeIndex
    mock_income_data.columns = pd.to_datetime(mock_income_data.columns)
    mock_cashflow_data.columns = pd.to_datetime(mock_cashflow_data.columns)
    
    # Mock the yfinance ticker object
    mock_ticker_instance = Mock()
    mock_ticker_instance.quarterly_income_stmt = mock_income_data
    mock_ticker_instance.quarterly_cashflow = mock_cashflow_data
    mock_ticker_instance.quarterly_balance_sheet = pd.DataFrame()
    mock_ticker.return_value = mock_ticker_instance
    
    # This should not raise a DatetimeIndex comparison error
    result = compute_quarterly_series('TEST')
    
    assert isinstance(result, FundamentalsSeries)


def test_fundamentals_service_safe_get_method():
    """Test the _safe_get method handles DatetimeIndex properly."""
    service = FundamentalsService()
    
    # Create test DataFrame with DatetimeIndex columns
    test_data = pd.DataFrame({
        pd.Timestamp('2023-12-31'): [100, 200],
        pd.Timestamp('2023-09-30'): [110, 220]
    }, index=['Revenue', 'Income'])
    
    # Test that _safe_get doesn't raise DatetimeIndex comparison errors
    try:
        result = service._safe_get(test_data, 'Revenue', pd.Timestamp('2023-12-31'))
        # If we get here without an exception, the fix worked
        assert True
    except ValueError as e:
        if "ambiguous" in str(e).lower():
            pytest.fail("DatetimeIndex comparison error still exists")
        else:
            # Some other error is acceptable for this test
            pass


def test_fundamentals_service_calculate_growth_rate():
    """Test the _calculate_growth_rate method."""
    service = FundamentalsService()
    
    # Test normal growth calculation
    growth = service._calculate_growth_rate(120.0, 100.0)
    assert growth == pytest.approx(0.2)
    
    # Test negative growth
    growth = service._calculate_growth_rate(80.0, 100.0)
    assert growth == pytest.approx(-0.2)
    
    # Test with None values
    growth = service._calculate_growth_rate(None, 100.0)
    assert growth is None
    
    growth = service._calculate_growth_rate(120.0, None)
    assert growth is None
    
    # Test with zero previous value
    growth = service._calculate_growth_rate(100.0, 0.0)
    assert growth is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])