"""FastAPI router for fundamentals endpoints."""

import json
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
import asyncio
import time

from backend.models.fundamentals import (
    FundamentalsResponse,
    FundamentalsTTM,
    FundamentalsSeries,
    CompareRequest,
    ScreenerRequest,
    ScreenerResponse
)
from backend.services.fundamentals import (
    compute_ttm_metrics,
    compute_quarterly_series
)

# Import authentication dependency
# We need to import this from the main api module
def verify_password_dependency(password: str = Query(..., description="Password")):
    """Simple password verification for fundamentals routes"""
    import os
    from fastapi import HTTPException, status
    
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") 
    GUEST_PASSWORD = os.getenv("GUEST_PASSWORD")
    MASTER_PASSWORD = os.getenv("STOCKSCOPE_PASSWORD", ADMIN_PASSWORD)
    
    valid_passwords = [ADMIN_PASSWORD, DEMO_PASSWORD, GUEST_PASSWORD, MASTER_PASSWORD]
    valid_passwords = [p for p in valid_passwords if p]  # Remove None values
    
    if password not in valid_passwords:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    return password

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])

def load_sp500_universe() -> List[str]:
    """Load S&P 500 universe from JSON file."""
    try:
        sp500_path = os.path.join(os.path.dirname(__file__), "..", "data", "universe", "sp500.json")
        with open(sp500_path, 'r') as f:
            return json.load(f)
    except Exception:
        # Fallback to a small set if file not found
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]


@router.get("/{ticker}/ttm", response_model=FundamentalsTTM)
async def get_ttm_fundamentals(ticker: str, current_user: str = Depends(verify_password_dependency)):
    """Get TTM fundamentals data for a single ticker."""
    try:
        ticker = ticker.upper()
        ttm_data = compute_ttm_metrics(ticker)
        return ttm_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching TTM fundamentals for {ticker}: {str(e)}"
        )


@router.get("/{ticker}/series", response_model=FundamentalsSeries)
async def get_series_fundamentals(ticker: str, current_user: str = Depends(verify_password_dependency)):
    """Get series fundamentals data for a single ticker."""
    try:
        ticker = ticker.upper()
        series_data = compute_quarterly_series(ticker)
        return series_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching series fundamentals for {ticker}: {str(e)}"
        )


@router.get("/{ticker}", response_model=FundamentalsResponse)
async def get_fundamentals(ticker: str, current_user: str = Depends(verify_password_dependency)):
    """Get fundamentals data (TTM and series) for a single ticker."""
    try:
        ticker = ticker.upper()
        
        # Compute TTM and series data
        ttm_data = compute_ttm_metrics(ticker)
        series_data = compute_quarterly_series(ticker)
        
        return FundamentalsResponse(
            ttm=ttm_data,
            series=series_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching fundamentals for {ticker}: {str(e)}"
        )


@router.post("/compare", response_model=List[FundamentalsTTM])
async def compare_fundamentals(request: CompareRequest, current_user: str = Depends(verify_password_dependency)):
    """Compare TTM fundamentals across multiple tickers."""
    try:
        if not request.tickers:
            raise HTTPException(status_code=400, detail="No tickers provided")
        
        if len(request.tickers) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 tickers allowed")
        
        results = []
        for ticker in request.tickers:
            ticker = ticker.upper()
            try:
                ttm_data = compute_ttm_metrics(ticker)
                results.append(ttm_data)
                # Small delay to respect rate limits
                time.sleep(0.1)
            except Exception as e:
                # Continue with other tickers even if one fails
                print(f"Error processing {ticker}: {e}")
                continue
        
        # Sort by revenue_ttm (descending)
        results.sort(
            key=lambda x: x.revenue_ttm if x.revenue_ttm else 0,
            reverse=True
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing fundamentals: {str(e)}"
        )


@router.post("/screener", response_model=ScreenerResponse)
async def screen_fundamentals(request: ScreenerRequest, current_user: str = Depends(verify_password_dependency)):
    """Screen stocks based on fundamental criteria."""
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
                ttm_data = compute_ttm_metrics(ticker)
                total_screened += 1
                
                # Skip if insufficient data
                if ttm_data.insufficient_data:
                    continue
                
                # Apply filters
                passed_filters = True
                
                # Revenue growth filter
                if (request.min_revenue_growth_yoy is not None and
                    (ttm_data.revenue_growth_yoy is None or 
                     ttm_data.revenue_growth_yoy < request.min_revenue_growth_yoy)):
                    passed_filters = False
                
                # FCF growth filter
                if (request.min_fcf_growth_yoy is not None and
                    (ttm_data.fcf_growth_yoy is None or 
                     ttm_data.fcf_growth_yoy < request.min_fcf_growth_yoy)):
                    passed_filters = False
                
                # Margin growth filter (percentage points)
                if (request.min_margin_growth_yoy_pp is not None and
                    (ttm_data.margin_growth_yoy_pp is None or 
                     ttm_data.margin_growth_yoy_pp < request.min_margin_growth_yoy_pp)):
                    passed_filters = False
                
                # EBITDA growth filter
                if (request.min_ebitda_growth_yoy is not None and
                    (ttm_data.ebitda_growth_yoy is None or 
                     ttm_data.ebitda_growth_yoy < request.min_ebitda_growth_yoy)):
                    passed_filters = False
                
                # Debt to cash filter
                if (request.max_debt_to_cash is not None and
                    (ttm_data.debt_to_cash is None or 
                     ttm_data.debt_to_cash > request.max_debt_to_cash)):
                    passed_filters = False
                
                if passed_filters:
                    results.append(ttm_data)
                
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
        
        results.sort(
            key=lambda x: getattr(x, sort_field) if getattr(x, sort_field) is not None else -999999,
            reverse=sort_reverse
        )
        
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


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fundamentals"}