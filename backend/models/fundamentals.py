"""Pydantic models for fundamentals data."""

from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class FundamentalPoint(BaseModel):
    """A single fundamental data point with date and value."""
    date: datetime
    value: Optional[float] = None


class FundamentalsSeries(BaseModel):
    """Time series of fundamental metrics for charting."""
    revenue_q: List[FundamentalPoint]
    operating_income_q: List[FundamentalPoint]
    operating_margin_q: List[FundamentalPoint]  # as decimal (0.21 = 21%)
    fcf_q: List[FundamentalPoint]
    fcf_margin_q: List[FundamentalPoint]  # as decimal
    ebitda_q: List[FundamentalPoint]


class FundamentalsTTM(BaseModel):
    """TTM (trailing twelve months) fundamental metrics."""
    ticker: str
    revenue_ttm: Optional[float] = None
    operating_income_ttm: Optional[float] = None
    operating_margin_ttm: Optional[float] = None  # as decimal
    fcf_ttm: Optional[float] = None
    fcf_margin_ttm: Optional[float] = None  # as decimal
    ebitda_ttm: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None  # as decimal
    fcf_growth_yoy: Optional[float] = None  # as decimal
    ebitda_growth_yoy: Optional[float] = None  # as decimal
    margin_growth_yoy_pp: Optional[float] = None  # percentage points
    debt_to_cash: Optional[float] = None
    insufficient_data: bool = False


class FundamentalsResponse(BaseModel):
    """Combined response with TTM and series data."""
    ttm: FundamentalsTTM
    series: FundamentalsSeries


class CompareRequest(BaseModel):
    """Request body for comparing multiple tickers."""
    tickers: List[str]


class ScreenerRequest(BaseModel):
    """Request body for screener filters."""
    universe: Optional[List[str]] = None
    min_revenue_growth_yoy: Optional[float] = None
    min_fcf_growth_yoy: Optional[float] = None
    min_margin_growth_yoy_pp: Optional[float] = None
    min_ebitda_growth_yoy: Optional[float] = None
    max_debt_to_cash: Optional[float] = None
    limit: int = 100
    sort_by: str = "revenue_growth_yoy"
    sort_dir: str = "desc"


class ScreenerResponse(BaseModel):
    """Response from screener with filtered results."""
    results: List[FundamentalsTTM]
    total_screened: int
    filters_applied: dict