"""Fundamentals data service for fetching and computing financial metrics."""

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import yfinance as yf

# Import the Pydantic models instead of using dataclass
from backend.models.fundamentals import FundamentalsTTM, FundamentalsSeries, FundamentalPoint

# ---------- helpers

def _row(df: Optional[pd.DataFrame], aliases: List[str]) -> pd.Series:
    """Return numeric Series with DateTimeIndex ascending (or empty Series)."""
    if df is None or getattr(df, "empty", True):
        return pd.Series(dtype="float64")
    for a in aliases:
        if a in df.index:
            s = df.loc[a]
            s = pd.to_numeric(s, errors="coerce").dropna()
            s.index = pd.to_datetime(s.index)
            return s.sort_index()
    return pd.Series(dtype="float64")

def _exists(s: Optional[pd.Series]) -> bool:
    return isinstance(s, pd.Series) and not s.empty

def _ttm(s: pd.Series) -> Optional[float]:
    if not _exists(s): return None
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.shape[0] < 4: return None
    return float(s.tail(4).sum())

def _yoy_from_ttm(s: pd.Series) -> Optional[float]:
    if not _exists(s): return None
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.shape[0] < 8: return None
    curr = float(s.tail(4).sum())
    prev = float(s.iloc[-8:-4].sum())
    if prev == 0: return None
    return (curr - prev) / prev

def _margin_series(numer: pd.Series, denom: pd.Series) -> pd.Series:
    numer = pd.to_numeric(numer, errors="coerce")
    denom = pd.to_numeric(denom, errors="coerce")
    df = pd.concat([numer, denom], axis=1).dropna()
    if df.shape[0] == 0: 
        return pd.Series(dtype="float64")
    return (df.iloc[:, 0] / df.iloc[:, 1]).sort_index()

def _latest(s: pd.Series) -> Optional[float]:
    if not _exists(s): return None
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if s.empty: return None
    return float(s.iloc[-1])

# ---------- core data pulls

def fetch_quarterlies(ticker: str) -> Dict[str, pd.Series]:
    t = yf.Ticker(ticker)
    fin = t.quarterly_financials
    cf  = t.quarterly_cashflow
    bs  = t.quarterly_balance_sheet

    revenue = _row(fin, ["Total Revenue", "TotalRevenue"])
    op_inc  = _row(fin, ["Operating Income", "OperatingIncome"])
    ebitda  = _row(fin, ["EBITDA"])

    ocf     = _row(cf,  ["Operating Cash Flow", "Total Cash From Operating Activities"])
    capex   = _row(cf,  ["Capital Expenditures"])
    fcf     = (ocf - capex).dropna()

    total_debt = _row(bs, ["Total Debt"])
    if total_debt.empty:
        short_lt = _row(bs, ["Short Long Term Debt"])
        long_t   = _row(bs, ["Long Term Debt"])
        if not short_lt.empty or not long_t.empty:
            total_debt = (short_lt.fillna(0) + long_t.fillna(0))

    cash = _row(bs, ["Cash And Cash Equivalents", "Cash"])
    sti  = _row(bs, ["Short Term Investments"])
    cash_and_sti = (cash.fillna(0) + sti.fillna(0)).replace({0: pd.NA})

    return {
        "revenue": revenue,
        "op_inc": op_inc,
        "ebitda": ebitda,
        "fcf": fcf,
        "debt": total_debt,
        "cash_and_sti": cash_and_sti,
        # keep raw for series charts if you need them:
        "ocf": ocf, "capex": capex,
    }

# ---------- public API

def compute_ttm_metrics(ticker: str) -> FundamentalsTTM:
    q = fetch_quarterlies(ticker)

    rev_ttm     = _ttm(q["revenue"])
    opi_ttm     = _ttm(q["op_inc"])
    ebitda_ttm  = _ttm(q["ebitda"])
    fcf_ttm     = _ttm(q["fcf"])
    rev_yoy     = _yoy_from_ttm(q["revenue"])
    fcf_yoy     = _yoy_from_ttm(q["fcf"])
    ebitda_yoy  = _yoy_from_ttm(q["ebitda"])

    opm_ttm = None
    if rev_ttm is not None and rev_ttm != 0 and opi_ttm is not None:
        opm_ttm = opi_ttm / rev_ttm

    margin_growth_pp = None
    if _exists(q["op_inc"]) and _exists(q["revenue"]) and \
       q["op_inc"].shape[0] >= 8 and q["revenue"].shape[0] >= 8:
        curr = q["op_inc"].tail(4).sum() / q["revenue"].tail(4).sum()
        prev = q["op_inc"].iloc[-8:-4].sum() / q["revenue"].iloc[-8:-4].sum()
        margin_growth_pp = (curr - prev) * 100.0

    total_debt = _latest(q["debt"])
    cash_eq    = _latest(q["cash_and_sti"])
    net_debt   = None if total_debt is None or cash_eq is None else (total_debt - cash_eq)
    debt_to_cash = None
    if cash_eq is not None and cash_eq != 0 and total_debt is not None:
        debt_to_cash = total_debt / cash_eq

    insufficient = (not _exists(q["revenue"]) or not _exists(q["op_inc"]) or
                    q["revenue"].shape[0] < 3 or q["op_inc"].shape[0] < 3)

    fcf_margin_ttm = None
    if rev_ttm is not None and rev_ttm != 0 and fcf_ttm is not None:
        fcf_margin_ttm = fcf_ttm / rev_ttm

    return FundamentalsTTM(
        ticker=ticker.upper(),
        revenue_ttm=rev_ttm,
        operating_income_ttm=opi_ttm,
        operating_margin_ttm=opm_ttm,
        fcf_ttm=fcf_ttm,
        fcf_margin_ttm=fcf_margin_ttm,
        ebitda_ttm=ebitda_ttm,
        revenue_growth_yoy=rev_yoy,
        fcf_growth_yoy=fcf_yoy,
        ebitda_growth_yoy=ebitda_yoy,
        margin_growth_yoy_pp=margin_growth_pp,
        total_debt=total_debt,
        cash_and_equivalents=cash_eq,
        net_debt=net_debt,
        debt_to_cash=debt_to_cash,
        insufficient_data=insufficient,
    )

# Simple service wrapper to match your debug script calls
class FundamentalsService:
    def get_fundamentals_data(self, ticker: str) -> dict:
        ttm = compute_ttm_metrics(ticker)
        q = fetch_quarterlies(ticker)
        return {
            "ticker": ttm.ticker,
            "ttm": ttm.__dict__,
            "series": {
                "revenue_q": q["revenue"].to_dict(),
                "op_inc_q": q["op_inc"].to_dict(),
                "ebitda_q": q["ebitda"].to_dict(),
                "fcf_q": q["fcf"].to_dict(),
            },
            "metadata": {
                "data_type": "quarterly",
                "periods_available": int(q["revenue"].shape[0]),
                "last_updated": datetime.utcnow().isoformat(),
                "insufficient_data": ttm.insufficient_data,
            },
        }

_service = FundamentalsService()
def get_service() -> FundamentalsService:
    return _service

# Add missing function that the router expects
def compute_quarterly_series(ticker: str):
    """Compute quarterly series data for a ticker - wrapper for router compatibility"""
    from backend.models.fundamentals import FundamentalsSeries, FundamentalPoint
    
    q = fetch_quarterlies(ticker)
    
    # Convert series data to the format expected by FundamentalsSeries
    revenue_q = []
    operating_income_q = []
    operating_margin_q = []
    fcf_q = []
    fcf_margin_q = []
    ebitda_q = []
    
    # Get the time index (sorted ascending for proper chronological order)
    if not q["revenue"].empty:
        dates = q["revenue"].index.sort_values()
        
        for date in dates:
            # Revenue
            revenue_val = q["revenue"].get(date) if date in q["revenue"].index else None
            revenue_q.append(FundamentalPoint(date=date.to_pydatetime(), value=revenue_val))
            
            # Operating Income
            op_inc_val = q["op_inc"].get(date) if date in q["op_inc"].index else None
            operating_income_q.append(FundamentalPoint(date=date.to_pydatetime(), value=op_inc_val))
            
            # Operating Margin
            if revenue_val and revenue_val != 0 and op_inc_val:
                margin_val = op_inc_val / revenue_val
            else:
                margin_val = None
            operating_margin_q.append(FundamentalPoint(date=date.to_pydatetime(), value=margin_val))
            
            # FCF
            fcf_val = q["fcf"].get(date) if date in q["fcf"].index else None
            fcf_q.append(FundamentalPoint(date=date.to_pydatetime(), value=fcf_val))
            
            # FCF Margin
            if revenue_val and revenue_val != 0 and fcf_val:
                fcf_margin_val = fcf_val / revenue_val
            else:
                fcf_margin_val = None
            fcf_margin_q.append(FundamentalPoint(date=date.to_pydatetime(), value=fcf_margin_val))
            
            # EBITDA
            ebitda_val = q["ebitda"].get(date) if date in q["ebitda"].index else None
            ebitda_q.append(FundamentalPoint(date=date.to_pydatetime(), value=ebitda_val))
    
    return FundamentalsSeries(
        revenue_q=revenue_q,
        operating_income_q=operating_income_q,
        operating_margin_q=operating_margin_q,
        fcf_q=fcf_q,
        fcf_margin_q=fcf_margin_q,
        ebitda_q=ebitda_q
    )