"""Fundamentals API endpoints for financial metrics analysis."""

from typing import List, Dict, Any, Optional
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.cache import cached, peek_many
from backend.core.auth import verify_password_with_role
from backend.services.fundamentals import compute_ttm_metrics, compute_quarterly_series, compact
from backend.models.fundamentals import (
    FundamentalsTTM, FundamentalsSeries, FundamentalsResponse,
    CompareRequest, ScreenerRequest, ScreenerResponse
)
from backend.data.universe.sp500 import load_sp500_universe, CURATED_UNIVERSE_NAME
from backend.services.research import normalized_symbol, saved_sec_facts
from backend.services.sec_facts import is_sec_configured

router = APIRouter()


@router.get("/{ticker}/preview")
async def get_saved_preview(ticker: str, current_user: str = Depends(verify_password_with_role)):
    """Quick views only read existing cache entries, including dated last-good data."""
    try:
        symbol = normalized_symbol(ticker)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    saved = (await asyncio.to_thread(peek_many, '_compute_full_cached', [symbol])).get(symbol)
    metadata = (saved or {}).get('metadata') or {}
    return {'symbol': symbol, 'saved': saved is not None,
            'ttm': (saved or {}).get('ttm'),
            'metadata': {key: metadata.get(key) for key in ('retrieved_at', 'source', 'currency')}}


@router.get("/{ticker}/sec-facts")
async def get_saved_sec_facts(
    ticker: str,
    concept: Optional[str] = Query(default=None, max_length=200),
    unit: Optional[str] = Query(default=None, max_length=100),
    offset: int = Query(default=0, ge=0, le=1000000),
    limit: int = Query(default=200, ge=1, le=200),
    current_user: str = Depends(verify_password_with_role),
):
    """Read a saved SEC snapshot. This route never contacts external providers."""
    try:
        symbol = normalized_symbol(ticker)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    snapshot = await asyncio.to_thread(saved_sec_facts, symbol)
    configured = is_sec_configured()
    rows = [row for row in (snapshot or {}).get("facts", []) if isinstance(row, dict)]
    concepts = {}
    for row in rows:
        key = f"{row.get('taxonomy', '')}:{row.get('concept', '')}"
        if key not in concepts:
            concepts[key] = {"key": key, "taxonomy": row.get("taxonomy"), "concept": row.get("concept"),
                             "label": row.get("label"), "units": set(), "count": 0}
        concepts[key]["count"] += 1
        if isinstance(row.get("unit"), str):
            concepts[key]["units"].add(row["unit"])
    options = [{**item, "units": sorted(item["units"])} for _, item in sorted(concepts.items())]
    filtered = [row for row in rows if
                (concept is None or f"{row.get('taxonomy', '')}:{row.get('concept', '')}" == concept)
                and (unit is None or row.get("unit") == unit)]
    # Stable newest-filing-first ordering; unknown dates remain at the end.
    filtered.sort(key=lambda row: (row.get("filed") or "", row.get("end") or "", row.get("fact_id") or ""), reverse=True)
    return {"symbol": symbol, "configured": configured, "saved": snapshot is not None,
            "status": (snapshot or {}).get("status", "not_saved"), "cik": (snapshot or {}).get("cik"),
            "entity_name": (snapshot or {}).get("entity_name"), "metadata": (snapshot or {}).get("metadata") or {},
            "facts": filtered[offset:offset + limit], "total": len(filtered), "total_saved": len(rows),
            "offset": offset, "limit": limit, "has_more": offset + limit < len(filtered), "concepts": options}


def _compute_ttm_cached(ticker: str) -> dict:
    """Cached TTM computation."""
    return _compute_full_cached(ticker)["ttm"]


def _compute_series_cached(ticker: str) -> dict:
    """Cached series computation."""
    return _compute_full_cached(ticker)["series"]


@cached
def _compute_full_cached(ticker: str) -> dict:
    """Cached full fundamentals computation."""
    from backend.services.fundamentals import get_service
    service = get_service()
    return service.get_fundamentals_data(ticker)


@router.get("/{ticker}/ttm")
async def get_ttm_fundamentals(ticker: str, current_user: str = Depends(verify_password_with_role)):
    """Get TTM fundamentals data for a single ticker - returns only available fields."""
    try:
        result = await asyncio.to_thread(_compute_ttm_cached, ticker.upper())
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching TTM data: {str(e)}")


@router.get("/{ticker}/series")
async def get_series_fundamentals(ticker: str, current_user: str = Depends(verify_password_with_role)):
    """Get series fundamentals data for a single ticker - returns only available series."""
    try:
        result = await asyncio.to_thread(_compute_series_cached, ticker.upper())
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching series data: {str(e)}")


@router.get("/{ticker}", response_model=FundamentalsResponse)
async def get_fundamentals(ticker: str, current_user: str = Depends(verify_password_with_role)):
    """Get fundamentals data (TTM and series) for a single ticker - compact format."""
    try:
        result = await asyncio.to_thread(_compute_full_cached, ticker.upper())
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fundamentals: {str(e)}")


@router.post("/compare")
async def compare_fundamentals(request: CompareRequest, current_user: str = Depends(verify_password_with_role)):
    """Compare TTM fundamentals across multiple tickers - returns compacted data."""
    try:
        if not request.tickers:
            raise HTTPException(status_code=400, detail="No tickers provided")
        
        if len(request.tickers) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 tickers allowed")
        
        try:
            tickers = list(dict.fromkeys(
                normalized_symbol(ticker).replace('.', '-') for ticker in request.tickers
            ))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        # Share the screener's bounded thread pool and timeout. A slow provider
        # must not block the event loop or discard the other companies.
        loop = asyncio.get_running_loop()
        raw_results = await asyncio.gather(
            *[_fetch_ticker_screener(ticker, loop) for ticker in tickers]
        )
        results = [row for row in raw_results if row]

        # Stable input order breaks revenue ties; missing values stay last,
        # distinct from observed zero or negative revenue.
        available = [row for row in results if row.get("revenue_ttm") is not None]
        missing = [row for row in results if row.get("revenue_ttm") is None]
        available.sort(key=lambda row: row["revenue_ttm"], reverse=True)
        results = available + missing
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing fundamentals: {str(e)}")


# Semaphore to cap concurrent yfinance calls (avoids hammering the API)
_SCREENER_CONCURRENCY = 2
_screener_semaphore = asyncio.Semaphore(_SCREENER_CONCURRENCY)


async def _fetch_ticker_screener(ticker: str, loop: asyncio.AbstractEventLoop) -> Optional[dict]:
    """Fetch one ticker's TTM data in a thread, with a per-ticker timeout."""
    async with _screener_semaphore:
        try:
            compacted = await asyncio.wait_for(
                loop.run_in_executor(None, _compute_ttm_cached, ticker),
                timeout=12.0,
            )
            return compacted
        except asyncio.TimeoutError:
            print(f"Screener timeout for {ticker}, skipping")
            return None
        except Exception as e:
            print(f"Error processing {ticker} in screener: {e}")
            return None


@router.post("/screener", response_model=ScreenerResponse)
async def screen_fundamentals(request: ScreenerRequest, current_user: str = Depends(verify_password_with_role)):
    """Screen stocks based on fundamental criteria - returns compacted results."""
    try:
        # The bundled list is curated and has no verified membership date.
        universe = request.universe if request.universe else load_sp500_universe()
        universe = list(dict.fromkeys(t.strip().upper().replace('.', '-') for t in universe if t.strip()))
        
        if len(universe) > 500:
            raise HTTPException(
                status_code=400, 
                detail="Universe too large (max 500 tickers)"
            )
        
        tickers = [t.upper() for t in universe]

        # A screen never fans out into hundreds of paid/rate-limited requests.
        # Individual company views populate the shared six-hour cache.
        def saved_rows():
            saved = peek_many('_compute_full_cached', tickers)
            return [saved.get(ticker, {}).get('ttm') for ticker in tickers]

        raw_results = await asyncio.to_thread(saved_rows)

        results = []
        total_screened = 0
        total_insufficient = 0

        for compacted in raw_results:
            if compacted is None:
                continue
            total_screened += 1

            # Skip if insufficient data
            if compacted.get("insufficient_data", True):
                total_insufficient += 1
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
        
        # Sort results
        valid_sort_fields = [
            'revenue_growth_yoy', 'fcf_growth_yoy', 'ebitda_growth_yoy',
            'fcf_margin_ttm', 'operating_margin_ttm', 'revenue_ttm'
        ]
        
        sort_field = request.sort_by if request.sort_by in valid_sort_fields else 'revenue_growth_yoy'
        sort_reverse = request.sort_dir.lower() == 'desc'
        
        # Keep missing values last for both ascending and descending order.
        available = [row for row in results if row.get(sort_field) is not None]
        missing = [row for row in results if row.get(sort_field) is None]
        available.sort(key=lambda row: row[sort_field], reverse=sort_reverse)
        results = available + missing
        
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
            filters_applied=filters_applied,
            total_attempted=len(tickers),
            total_failed=len(tickers) - total_screened,
            total_insufficient=total_insufficient,
            total_evaluated=total_screened - total_insufficient,
            total_matches=len(results),
            universe_name="Custom stock list" if request.universe else CURATED_UNIVERSE_NAME,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running screener: {str(e)}"
        )
