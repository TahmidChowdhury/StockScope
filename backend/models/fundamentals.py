"""Pydantic models for fundamentals data."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class FundamentalPoint(BaseModel):
    """A single fundamental data point with date and value."""
    date: datetime
    value: Optional[float] = None


class FundamentalsSeries(BaseModel):
    """Series data for fundamental metrics (quarterly)."""
    revenue_q: Optional[List[FundamentalPoint]] = None
    operating_income_q: Optional[List[FundamentalPoint]] = None
    operating_margin_q: Optional[List[FundamentalPoint]] = None
    fcf_q: Optional[List[FundamentalPoint]] = None
    fcf_margin_q: Optional[List[FundamentalPoint]] = None
    ebitda_q: Optional[List[FundamentalPoint]] = None

    class Config:
        # Exclude None values when serializing
        exclude_none = True


class FundamentalsTTM(BaseModel):
    """TTM (trailing twelve months) fundamental metrics - all fields optional except ticker."""
    ticker: str
    insufficient_data: bool = False
    
    # Core metrics - only present if data is available
    revenue_ttm: Optional[float] = None
    operating_income_ttm: Optional[float] = None
    operating_margin_ttm: Optional[float] = None  # as decimal
    fcf_ttm: Optional[float] = None
    fcf_margin_ttm: Optional[float] = None  # as decimal
    ebitda_ttm: Optional[float] = None
    
    # Growth metrics - only present if >=8 quarters available
    revenue_growth_yoy: Optional[float] = None  # as decimal
    fcf_growth_yoy: Optional[float] = None  # as decimal
    ebitda_growth_yoy: Optional[float] = None  # as decimal
    margin_growth_yoy_pp: Optional[float] = None  # percentage points
    
    # Debt metrics - only present if both debt and cash data available
    debt_to_cash: Optional[float] = None
    
    # Additional fields for debugging/future use
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    net_debt: Optional[float] = None

    class Config:
        # Exclude None values when serializing
        exclude_none = True


class FundamentalsResponse(BaseModel):
    """Combined response with TTM and series data."""
    ticker: str
    ttm: Dict[str, Any]  # Compacted TTM data
    series: Dict[str, Any]  # Compacted series data
    metadata: Dict[str, Any]

    class Config:
        exclude_none = True


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
    results: List[Dict[str, Any]]  # Use compacted dictionaries instead of full models
    total_screened: int
    filters_applied: Dict[str, Any]