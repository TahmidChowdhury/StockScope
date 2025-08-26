"""Fundamentals API endpoints for financial metrics analysis."""

from typing import List, Dict, Any
import time
import os
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.cache import cached
from backend.services.fundamentals import compute_ttm_metrics, compute_quarterly_series, compact
from backend.models.fundamentals import (
    FundamentalsTTM, FundamentalsSeries, FundamentalsResponse,
    CompareRequest, ScreenerRequest, ScreenerResponse
)
from backend.data.universe.sp500 import load_sp500_universe

router = APIRouter()

# Use the exact same authentication logic as the main API
async def verify_password_dependency(password: str = Query(..., description="Password")):
    """Use the same authentication logic as the main API for consistency"""
    
    # Load the same password variables as main API
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") 
    GUEST_PASSWORD = os.getenv("GUEST_PASSWORD")
    MASTER_PASSWORD = os.getenv("STOCKSCOPE_PASSWORD", ADMIN_PASSWORD)
    
    def get_user_role(password: str) -> str:
        """Determine user role based on password - same logic as main API"""
        if password == ADMIN_PASSWORD:
            return "admin"
        elif password == DEMO_PASSWORD:
            return "demo"
        elif password == GUEST_PASSWORD:
            return "guest"
        elif password == MASTER_PASSWORD:
            return "admin"  # Backward compatibility
        else:
            return None
    
    role = get_user_role(password)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    return role


@cached
def _compute_ttm_cached(ticker: str) -> dict:
    """Cached TTM computation."""
    ttm_data = compute_ttm_metrics(ticker)
    # Convert to dict and compact (exclude None values)
    ttm_dict = ttm_data.model_dump(exclude_none=True) if hasattr(ttm_data, 'model_dump') else ttm_data.__dict__
    return compact(ttm_dict)


@cached
def _compute_series_cached(ticker: str) -> dict:
    """Cached series computation."""
    series_data = compute_quarterly_series(ticker)
    # Convert to dict and compact (exclude None/empty values)
    series_dict = series_data.model_dump(exclude_none=True) if hasattr(series_data, 'model_dump') else series_data.__dict__
    return compact(series_dict)


@cached
def _compute_full_cached(ticker: str) -> dict:
    """Cached full fundamentals computation."""
    from backend.services.fundamentals import get_service
    service = get_service()
    return service.get_fundamentals_data(ticker)


@router.get("/{ticker}/ttm")
async def get_ttm_fundamentals(ticker: str, current_user: str = Depends(verify_password_dependency)):
    """Get TTM fundamentals data for a single ticker - returns only available fields."""
    try:
        result = _compute_ttm_cached(ticker.upper())
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching TTM data: {str(e)}")


@router.get("/{ticker}/series")
async def get_series_fundamentals(ticker: str, current_user: str = Depends(verify_password_dependency)):
    """Get series fundamentals data for a single ticker - returns only available series."""
    try:
        result = _compute_series_cached(ticker.upper())
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching series data: {str(e)}")


@router.get("/{ticker}", response_model=FundamentalsResponse)
async def get_fundamentals(ticker: str, current_user: str = Depends(verify_password_dependency)):
    """Get fundamentals data (TTM and series) for a single ticker - compact format."""
    try:
        result = _compute_full_cached(ticker.upper())
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fundamentals: {str(e)}")


@router.post("/compare")
async def compare_fundamentals(request: CompareRequest, current_user: str = Depends(verify_password_dependency)):
    """Compare TTM fundamentals across multiple tickers - returns compacted data."""
    try:
        if not request.tickers:
            raise HTTPException(status_code=400, detail="No tickers provided")
        
        if len(request.tickers) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 tickers allowed")
        
        results = []
        for ticker in request.tickers:
            ticker = ticker.upper()
            try:
                # Use cached computation
                compacted = _compute_ttm_cached(ticker)
                if compacted:  # Only include if we got some data
                    results.append(compacted)
                # Small delay to respect rate limits
                time.sleep(0.1)
            except Exception as e:
                # Continue with other tickers even if one fails
                print(f"Error processing {ticker}: {e}")
                continue
        
        # Sort by revenue_ttm (descending) if available
        def sort_key(x):
            return x.get("revenue_ttm", 0) if x.get("revenue_ttm") is not None else 0
        
        results.sort(key=sort_key, reverse=True)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing fundamentals: {str(e)}")


@router.post("/screener", response_model=ScreenerResponse)
async def screen_fundamentals(request: ScreenerRequest, current_user: str = Depends(verify_password_dependency)):
    """Screen stocks based on fundamental criteria - returns compacted results."""
    try:
        # Use provided universe or load S&P 500
        universe = request.universe if request.universe else load_sp500_universe()
        
        if len(universe) > 500:
            raise HTTPException(
                status_code=400, 
                detail="Universe too large (max 500 tickers)"
            )
        
        results = []
        total_screened = 0
        
        for ticker in universe:
            try:
                ticker = ticker.upper()
                # Use cached computation
                compacted = _compute_ttm_cached(ticker)
                total_screened += 1
                
                # Skip if insufficient data
                if compacted.get("insufficient_data", True):
                    continue
                
                # Apply filters - only check fields that exist
                passed_filters = True
                
                # Revenue growth filter
                if (request.min_revenue_growth_yoy is not None and
                    (compacted.get("revenue_growth_yoy") is None or 
                     compacted.get("revenue_growth_yoy") < request.min_revenue_growth_yoy)):
                    passed_filters = False
                
                # FCF growth filter
                if (request.min_fcf_growth_yoy is not None and
                    (compacted.get("fcf_growth_yoy") is None or 
                     compacted.get("fcf_growth_yoy") < request.min_fcf_growth_yoy)):
                    passed_filters = False
                
                # Margin growth filter (percentage points)
                if (request.min_margin_growth_yoy_pp is not None and
                    (compacted.get("margin_growth_yoy_pp") is None or 
                     compacted.get("margin_growth_yoy_pp") < request.min_margin_growth_yoy_pp)):
                    passed_filters = False
                
                # EBITDA growth filter
                if (request.min_ebitda_growth_yoy is not None and
                    (compacted.get("ebitda_growth_yoy") is None or 
                     compacted.get("ebitda_growth_yoy") < request.min_ebitda_growth_yoy)):
                    passed_filters = False
                
                # Debt to cash filter
                if (request.max_debt_to_cash is not None and
                    (compacted.get("debt_to_cash") is None or 
                     compacted.get("debt_to_cash") > request.max_debt_to_cash)):
                    passed_filters = False
                
                if passed_filters:
                    results.append(compacted)
                
                # Small delay to respect rate limits
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Error processing {ticker} in screener: {e}")
                continue
        
        # Sort results
        valid_sort_fields = [
            'revenue_growth_yoy', 'fcf_growth_yoy', 'ebitda_growth_yoy',
            'fcf_margin_ttm', 'operating_margin_ttm', 'revenue_ttm'
        ]
        
        sort_field = request.sort_by if request.sort_by in valid_sort_fields else 'revenue_growth_yoy'
        sort_reverse = request.sort_dir.lower() == 'desc'
        
        def sort_key(x):
            value = x.get(sort_field)
            return value if value is not None else -999999
        
        results.sort(key=sort_key, reverse=sort_reverse)
        
        # Apply limit
        limited_results = results[:request.limit]
        
        filters_applied = {
            'min_revenue_growth_yoy': request.min_revenue_growth_yoy,
            'min_fcf_growth_yoy': request.min_fcf_growth_yoy,
            'min_margin_growth_yoy_pp': request.min_margin_growth_yoy_pp,
            'min_ebitda_growth_yoy': request.min_ebitda_growth_yoy,
            'max_debt_to_cash': request.max_debt_to_cash,
            'sort_by': sort_field,
            'sort_dir': request.sort_dir
        }
        
        return ScreenerResponse(
            results=limited_results,
            total_screened=total_screened,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running screener: {str(e)}"
        )