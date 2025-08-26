"""Fundamentals data service for fetching and computing financial metrics."""

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import yfinance as yf
import os
import logging

# Import the Pydantic models instead of using dataclass
from backend.models.fundamentals import FundamentalsTTM, FundamentalsSeries, FundamentalPoint

# Debug logging setup
LOG = logging.getLogger("fund")
if os.getenv("FUND_DEBUG") == "1":
    logging.basicConfig(level=logging.DEBUG)
    LOG.setLevel(logging.DEBUG)

# ---------- helpers

def compact(d: dict) -> dict:
    """Remove None values and NaN from dictionary."""
    out = {}
    for k, v in d.items():
        if v is None: 
            continue
        if isinstance(v, float) and (pd.isna(v) or pd.isnull(v)):
            continue
        if isinstance(v, pd.Series) and v.empty:
            continue
        if isinstance(v, list) and len(v) == 0:
            continue
        out[k] = v
    return out

def _row(df: Optional[pd.DataFrame], aliases: List[str]) -> pd.Series:
    """Return numeric Series with DateTimeIndex ascending (or empty Series)."""
    if df is None or df.empty:
        return pd.Series(dtype="float64")
    
    for alias in aliases:
        if alias in df.index:
            s = df.loc[alias]
            s = pd.to_numeric(s, errors="coerce").dropna()
            if not s.empty:
                s.index = pd.to_datetime(s.index)
                return s.sort_index()
    
    return pd.Series(dtype="float64")

def _exists(s: Optional[pd.Series]) -> bool:
    """Safe existence check for series."""
    return s is not None and isinstance(s, pd.Series) and not s.empty

def _ttm(s: pd.Series) -> Optional[float]:
    """Calculate TTM sum with safe checks."""
    if not _exists(s): 
        return None
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.shape[0] < 4: 
        return None
    return float(s.tail(4).sum())

def _yoy_from_ttm(s: pd.Series) -> Optional[float]:
    """Calculate YoY growth from TTM data - requires >=8 quarters."""
    if not _exists(s): 
        return None
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.shape[0] < 8: 
        return None
    curr = float(s.tail(4).sum())
    prev = float(s.iloc[-8:-4].sum())
    if prev == 0: 
        return None
    return (curr - prev) / prev

def _margin_series(numer: pd.Series, denom: pd.Series) -> pd.Series:
    """Calculate margin series safely."""
    if not _exists(numer) or not _exists(denom):
        return pd.Series(dtype="float64")
    
    numer = pd.to_numeric(numer, errors="coerce")
    denom = pd.to_numeric(denom, errors="coerce")
    df = pd.concat([numer, denom], axis=1).dropna()
    if df.shape[0] == 0: 
        return pd.Series(dtype="float64")
    return (df.iloc[:, 0] / df.iloc[:, 1]).sort_index()

def _latest(s: pd.Series) -> Optional[float]:
    """Get latest value from series safely."""
    if not _exists(s): 
        return None
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.empty: 
        return None
    return float(s.iloc[-1])

# ---------- core data pulls

def fetch_quarterlies(ticker: str) -> Dict[str, pd.Series]:
    """Fetch quarterly data with expanded aliases and fallbacks."""
    try:
        t = yf.Ticker(ticker)
        fin = t.quarterly_financials
        cf = t.quarterly_cashflow
        bs = t.quarterly_balance_sheet

        # Revenue (Income Statement)
        revenue = _row(fin, [
            "Total Revenue", "TotalRevenue", "Revenue", "Net Revenue"
        ])
        
        # Operating Income (Income Statement)
        op_inc = _row(fin, [
            "Operating Income", "OperatingIncome", "Operating Profit", 
            "Income From Operations", "Operating Income Loss"
        ])
        
        # EBITDA (Income Statement)
        ebitda = _row(fin, [
            "EBITDA", "Ebitda", "EBITDA Normalized"
        ])

        # Operating Cash Flow (Cash Flow Statement)
        ocf = _row(cf, [
            "Operating Cash Flow", "Total Cash From Operating Activities",
            "CashFromOperatingActivities", "Net Cash From Operating Activities"
        ])

        # Capital Expenditures (Cash Flow Statement) - Expanded aliases
        capex = _row(cf, [
            "Capital Expenditures", "Investments", "Purchase Of PPE", 
            "PurchaseOfPPE", "Capital Expenditure", "Capex", "PPE Purchase",
            "Purchase Of Property Plant Equipment", "Acquisition Of PPE"
        ])

        # FCF calculation with fallback
        fcf = pd.Series(dtype="float64")
        if _exists(ocf):
            if _exists(capex):
                # Standard FCF = OCF - CapEx
                fcf = (ocf - capex.abs()).dropna().sort_index()  # Make capex positive
                LOG.debug("[fund] FCF calculated for %s using OCF - CapEx", ticker)
            else:
                # Fallback: FCF = OCF (when CapEx missing)
                fcf = ocf.copy().sort_index()
                LOG.debug("[fund] FCF fallback for %s: using OCF only (no CapEx data)", ticker)
        else:
            LOG.debug("[fund] No FCF for %s: missing OCF", ticker)

        # Total Debt (Balance Sheet)
        total_debt = _row(bs, ["Total Debt", "TotalDebt"])
        if not _exists(total_debt):
            # Fallback: Sum of short-term and long-term debt
            short_lt = _row(bs, ["Short Long Term Debt", "ShortLongTermDebt"])
            long_t = _row(bs, ["Long Term Debt", "LongTermDebt", "Long Term Debt Total"])
            if _exists(short_lt) or _exists(long_t):
                short_filled = short_lt.fillna(0) if _exists(short_lt) else pd.Series([0] * len(long_t.index), index=long_t.index)
                long_filled = long_t.fillna(0) if _exists(long_t) else pd.Series([0] * len(short_lt.index), index=short_lt.index)
                total_debt = (short_filled + long_filled).replace({0: pd.NA})
                LOG.debug("[fund] Debt calculated for %s using short + long term", ticker)
            else:
                LOG.debug("[fund] No debt data for %s", ticker)

        # Cash & Cash Equivalents (Balance Sheet) - Expanded aliases
        cash = _row(bs, [
            "Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash",
            "CashAndShortTermInvestments", "Cash Equivalents", "Total Cash"
        ])

        # Short Term Investments (Balance Sheet)
        sti = _row(bs, [
            "Short Term Investments", "ShortTermInvestments", 
            "Marketable Securities", "Short Term Marketable Securities"
        ])

        # Cash total calculation with fallback
        cash_and_sti = pd.Series(dtype="float64")
        if _exists(cash):
            cash_total = cash.fillna(0)
            if _exists(sti):
                cash_and_sti = (cash_total + sti.fillna(0)).replace({0: pd.NA})
                LOG.debug("[fund] Cash total for %s: cash + short term investments", ticker)
            else:
                cash_and_sti = cash.copy()
                LOG.debug("[fund] Cash total for %s: cash only (no STI)", ticker)
        else:
            LOG.debug("[fund] No cash data for %s", ticker)

        # Debug logging for missing data
        if not _exists(revenue):
            LOG.debug("[fund] No revenue for %s; income statement rows: %s", ticker, list(fin.index) if not fin.empty else [])
        if not _exists(capex):
            LOG.debug("[fund] No CapEx for %s; cashflow rows: %s", ticker, list(cf.index) if not cf.empty else [])
        if not _exists(cash_and_sti):
            LOG.debug("[fund] No cash for %s; balance sheet rows: %s", ticker, list(bs.index) if not bs.empty else [])

        return {
            "revenue": revenue,
            "op_inc": op_inc,
            "ebitda": ebitda,
            "fcf": fcf,
            "debt": total_debt,
            "cash_and_sti": cash_and_sti,
            # Keep raw data for series charts
            "ocf": ocf, 
            "capex": capex,
        }

    except Exception as e:
        LOG.error("[fund] Error fetching quarterly data for %s: %s", ticker, str(e))
        return {
            "revenue": pd.Series(dtype="float64"),
            "op_inc": pd.Series(dtype="float64"),
            "ebitda": pd.Series(dtype="float64"),
            "fcf": pd.Series(dtype="float64"),
            "debt": pd.Series(dtype="float64"),
            "cash_and_sti": pd.Series(dtype="float64"),
            "ocf": pd.Series(dtype="float64"),
            "capex": pd.Series(dtype="float64"),
        }

# ---------- public API

def compute_ttm_metrics(ticker: str) -> FundamentalsTTM:
    """Compute TTM metrics with proper null handling and omit missing fields."""
    q = fetch_quarterlies(ticker)

    # Basic TTM calculations
    rev_ttm = _ttm(q["revenue"])
    opi_ttm = _ttm(q["op_inc"])
    ebitda_ttm = _ttm(q["ebitda"])
    fcf_ttm = _ttm(q["fcf"])

    # YoY growth calculations (only if >=8 quarters available)
    rev_yoy = _yoy_from_ttm(q["revenue"])
    fcf_yoy = _yoy_from_ttm(q["fcf"])
    ebitda_yoy = _yoy_from_ttm(q["ebitda"])

    # Operating margin TTM
    opm_ttm = None
    if rev_ttm is not None and rev_ttm != 0 and opi_ttm is not None:
        opm_ttm = opi_ttm / rev_ttm

    # FCF margin TTM
    fcf_margin_ttm = None
    if rev_ttm is not None and rev_ttm != 0 and fcf_ttm is not None:
        fcf_margin_ttm = fcf_ttm / rev_ttm

    # Margin growth (percentage points)
    margin_growth_pp = None
    if (_exists(q["op_inc"]) and _exists(q["revenue"]) and 
        q["op_inc"].shape[0] >= 8 and q["revenue"].shape[0] >= 8):
        curr_margin = q["op_inc"].tail(4).sum() / q["revenue"].tail(4).sum()
        prev_margin = q["op_inc"].iloc[-8:-4].sum() / q["revenue"].iloc[-8:-4].sum()
        margin_growth_pp = (curr_margin - prev_margin) * 100.0

    # Debt metrics
    total_debt = _latest(q["debt"])
    cash_eq = _latest(q["cash_and_sti"])
    
    # Debt to cash ratio (only when both exist and cash != 0)
    debt_to_cash = None
    if total_debt is not None and cash_eq is not None and cash_eq != 0:
        debt_to_cash = total_debt / cash_eq

    # Net debt
    net_debt = None
    if total_debt is not None and cash_eq is not None:
        net_debt = total_debt - cash_eq

    # Insufficient data flag
    insufficient = (not _exists(q["revenue"]) or not _exists(q["op_inc"]) or
                    q["revenue"].shape[0] < 3 or q["op_inc"].shape[0] < 3)

    # Build result dict with only available fields
    result_dict = {
        "ticker": ticker.upper(),
        "insufficient_data": insufficient,
    }

    # Add fields only if they have valid values
    if rev_ttm is not None:
        result_dict["revenue_ttm"] = rev_ttm
    if opi_ttm is not None:
        result_dict["operating_income_ttm"] = opi_ttm
    if opm_ttm is not None:
        result_dict["operating_margin_ttm"] = opm_ttm
    if fcf_ttm is not None:
        result_dict["fcf_ttm"] = fcf_ttm
    if fcf_margin_ttm is not None:
        result_dict["fcf_margin_ttm"] = fcf_margin_ttm
    if ebitda_ttm is not None:
        result_dict["ebitda_ttm"] = ebitda_ttm
    if rev_yoy is not None:
        result_dict["revenue_growth_yoy"] = rev_yoy
    if fcf_yoy is not None:
        result_dict["fcf_growth_yoy"] = fcf_yoy
    if ebitda_yoy is not None:
        result_dict["ebitda_growth_yoy"] = ebitda_yoy
    if margin_growth_pp is not None:
        result_dict["margin_growth_yoy_pp"] = margin_growth_pp
    if debt_to_cash is not None:
        result_dict["debt_to_cash"] = debt_to_cash

    # Optional fields for debugging/future use
    if total_debt is not None:
        result_dict["total_debt"] = total_debt
    if cash_eq is not None:
        result_dict["cash_and_equivalents"] = cash_eq
    if net_debt is not None:
        result_dict["net_debt"] = net_debt

    return FundamentalsTTM(**result_dict)

def compute_quarterly_series(ticker: str):
    """Compute quarterly series data with proper null handling."""
    q = fetch_quarterlies(ticker)
    
    # Only include series that have data
    series_dict = {}
    
    if _exists(q["revenue"]):
        revenue_q = []
        dates = q["revenue"].index.sort_values()
        for date in dates:
            revenue_val = q["revenue"].get(date) if date in q["revenue"].index else None
            revenue_q.append(FundamentalPoint(date=date.to_pydatetime(), value=revenue_val))
        series_dict["revenue_q"] = revenue_q

    if _exists(q["op_inc"]):
        operating_income_q = []
        dates = q["op_inc"].index.sort_values()
        for date in dates:
            op_inc_val = q["op_inc"].get(date) if date in q["op_inc"].index else None
            operating_income_q.append(FundamentalPoint(date=date.to_pydatetime(), value=op_inc_val))
        series_dict["operating_income_q"] = operating_income_q

    if _exists(q["revenue"]) and _exists(q["op_inc"]):
        operating_margin_q = []
        revenue_dates = set(q["revenue"].index)
        op_inc_dates = set(q["op_inc"].index)
        common_dates = sorted(revenue_dates.intersection(op_inc_dates))
        
        for date in common_dates:
            revenue_val = q["revenue"].get(date)
            op_inc_val = q["op_inc"].get(date)
            margin_val = None
            if revenue_val and revenue_val != 0 and op_inc_val:
                margin_val = op_inc_val / revenue_val
            operating_margin_q.append(FundamentalPoint(date=date.to_pydatetime(), value=margin_val))
        series_dict["operating_margin_q"] = operating_margin_q

    if _exists(q["fcf"]):
        fcf_q = []
        dates = q["fcf"].index.sort_values()
        for date in dates:
            fcf_val = q["fcf"].get(date) if date in q["fcf"].index else None
            fcf_q.append(FundamentalPoint(date=date.to_pydatetime(), value=fcf_val))
        series_dict["fcf_q"] = fcf_q

        # FCF Margin only if we have both FCF and revenue
        if _exists(q["revenue"]):
            fcf_margin_q = []
            revenue_dates = set(q["revenue"].index)
            fcf_dates = set(q["fcf"].index)
            common_dates = sorted(revenue_dates.intersection(fcf_dates))
            
            for date in common_dates:
                revenue_val = q["revenue"].get(date)
                fcf_val = q["fcf"].get(date)
                fcf_margin_val = None
                if revenue_val and revenue_val != 0 and fcf_val:
                    fcf_margin_val = fcf_val / revenue_val
                fcf_margin_q.append(FundamentalPoint(date=date.to_pydatetime(), value=fcf_margin_val))
            series_dict["fcf_margin_q"] = fcf_margin_q

    if _exists(q["ebitda"]):
        ebitda_q = []
        dates = q["ebitda"].index.sort_values()
        for date in dates:
            ebitda_val = q["ebitda"].get(date) if date in q["ebitda"].index else None
            ebitda_q.append(FundamentalPoint(date=date.to_pydatetime(), value=ebitda_val))
        series_dict["ebitda_q"] = ebitda_q

    return FundamentalsSeries(**series_dict)

# Simple service wrapper to match your debug script calls
class FundamentalsService:
    def get_fundamentals_data(self, ticker: str) -> dict:
        """Get comprehensive fundamentals data with compact response."""
        try:
            ttm = compute_ttm_metrics(ticker)
            series = compute_quarterly_series(ticker)
            q = fetch_quarterlies(ticker)
            
            # Convert to dict and compact (remove None values)
            ttm_dict = ttm.model_dump(exclude_none=True) if hasattr(ttm, 'model_dump') else ttm.__dict__
            series_dict = series.model_dump(exclude_none=True) if hasattr(series, 'model_dump') else series.__dict__
            
            ttm_out = compact(ttm_dict)
            series_out = compact(series_dict)
            
            metadata = {
                "data_type": "quarterly",
                "periods_available": int(q["revenue"].shape[0]) if _exists(q["revenue"]) else 0,
                "last_updated": datetime.utcnow().isoformat(),
                "insufficient_data": ttm.insufficient_data,
                "data_quality": {
                    "has_revenue": _exists(q["revenue"]),
                    "has_fcf": _exists(q["fcf"]),
                    "has_debt_cash": _exists(q["debt"]) and _exists(q["cash_and_sti"]),
                    "quarters_revenue": q["revenue"].shape[0] if _exists(q["revenue"]) else 0,
                    "quarters_fcf": q["fcf"].shape[0] if _exists(q["fcf"]) else 0,
                }
            }
            
            return compact({
                "ticker": ttm.ticker,
                "ttm": ttm_out,
                "series": series_out,
                "metadata": metadata,
            })
            
        except Exception as e:
            LOG.error("[fund] Error getting fundamentals for %s: %s", ticker, str(e))
            return {
                "ticker": ticker.upper(),
                "error": str(e),
                "metadata": {
                    "last_updated": datetime.utcnow().isoformat(),
                    "insufficient_data": True,
                }
            }

_service = FundamentalsService()
def get_service() -> FundamentalsService:
    return _service