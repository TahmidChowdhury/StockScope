"""Fundamentals data service for fetching and computing financial metrics."""

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime, timezone
import math
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
            s = pd.to_numeric(s, errors="coerce")
            s = s.where(s.map(lambda value: pd.notna(value) and math.isfinite(value)))
            if s.notna().any():
                s.index = pd.to_datetime(s.index)
                return s.sort_index()
    
    return pd.Series(dtype="float64")

def _exists(s: Optional[pd.Series]) -> bool:
    """Safe existence check for series."""
    return s is not None and isinstance(s, pd.Series) and not s.empty and bool(s.notna().any())

def _window(s: pd.Series, count: int, annual: bool = False) -> pd.Series:
    """Require consecutive reporting periods, including 52/53-week fiscal years.

    Dates are period ends, not publication dates. A missing period must never be
    replaced by an older observation to make a four-quarter total.
    """
    empty = pd.Series(dtype="float64")
    if not _exists(s):
        return empty
    clean = pd.to_numeric(s, errors="coerce").sort_index().tail(count)
    if len(clean) != count or clean.isna().any() or not clean.map(math.isfinite).all():
        return empty
    dates = pd.DatetimeIndex(clean.index)
    if dates.has_duplicates:
        return empty
    gaps = dates.to_series().diff().dropna().dt.days
    lower, upper = (350, 380) if annual else (75, 105)
    if not gaps.between(lower, upper).all():
        return empty
    return clean


def _ttm(s: pd.Series) -> Optional[float]:
    window = _window(s, 4)
    return float(window.sum()) if _exists(window) else None

def _yoy_from_ttm(s: pd.Series) -> Optional[float]:
    """Calculate YoY growth from TTM data - requires >=8 quarters."""
    s = _window(s, 8)
    if not _exists(s):
        return None
    curr = float(s.tail(4).sum())
    prev = float(s.iloc[-8:-4].sum())
    if prev <= 0:
        return None
    return (curr - prev) / prev

def _yoy_from_annual(s: pd.Series) -> Optional[float]:
    """Calculate YoY growth from annual data (last year vs prior year)."""
    s = _window(s, 2, annual=True)
    if not _exists(s):
        return None
    curr = float(s.iloc[-1])
    prev = float(s.iloc[-2])
    if prev <= 0:
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
    return (df.iloc[:, 0] / df.iloc[:, 1].replace(0, float('nan'))).dropna().sort_index()


def _growth_with_basis(quarterly: pd.Series, annual: pd.Series):
    """Prefer comparable TTM years; label annual fallback and undefined growth."""
    window = _window(quarterly, 8)
    basis = "ttm"
    if not _exists(window):
        window = _window(annual, 2, annual=True)
        basis = "fiscal_year"
    if not _exists(window):
        return None, {"basis": "unavailable", "status": "insufficient_history"}
    prior = float(window.iloc[:4].sum()) if basis == "ttm" else float(window.iloc[0])
    current = float(window.iloc[-4:].sum()) if basis == "ttm" else float(window.iloc[-1])
    metadata = {
        "basis": basis,
        "status": "available" if prior > 0 else "non_positive_prior",
        "current_period_end": window.index[-1].date().isoformat(),
        "prior_period_end": window.index[3 if basis == "ttm" else 0].date().isoformat(),
        "absolute_change": current - prior,
    }
    return ((current - prior) / prior if prior > 0 else None), metadata

def _latest(s: pd.Series) -> Optional[float]:
    """Get latest value from series safely."""
    if not _exists(s): 
        return None
    s = pd.to_numeric(s, errors="coerce").sort_index()
    if s.empty or pd.isna(s.iloc[-1]) or not math.isfinite(s.iloc[-1]):
        return None
    return float(s.iloc[-1])

# ---------- core data pulls

def fetch_annuals(ticker: str) -> Dict[str, pd.Series]:
    """Fetch annual data for YoY growth fallback."""
    try:
        t = yf.Ticker(ticker)
        fin = t.financials      # annual income statement
        cf = t.cashflow         # annual cash flow

        revenue = _row(fin, ["Total Revenue", "TotalRevenue", "Revenue", "Net Revenue"])
        op_inc  = _row(fin, ["Operating Income", "OperatingIncome", "Operating Profit"])
        ocf     = _row(cf, ["Operating Cash Flow", "Total Cash From Operating Activities",
                            "CashFromOperatingActivities"])
        capex   = _row(cf, ["Capital Expenditures", "Purchase Of PPE", "PurchaseOfPPE",
                            "Capital Expenditure", "Capex"])

        fcf = pd.Series(dtype="float64")
        if _exists(ocf) and _exists(capex):
            fcf = (ocf - capex.abs()).sort_index()

        return {"revenue": revenue, "op_inc": op_inc, "fcf": fcf}
    except Exception as e:
        LOG.error("[fund] Error fetching annual data for %s: %s", ticker, str(e))
        return {"revenue": pd.Series(dtype="float64"),
                "op_inc": pd.Series(dtype="float64"),
                "fcf": pd.Series(dtype="float64")}


def fetch_quarterlies(ticker: str) -> Dict[str, pd.Series]:
    """Fetch quarterly data with expanded aliases and fallbacks."""
    try:
        t = yf.Ticker(ticker)
        fin = t.quarterly_financials
        cf = t.quarterly_cashflow
        bs = t.quarterly_balance_sheet

        # Revenue (Income Statement) - expanded aliases
        revenue = _row(fin, [
            "Total Revenue", "TotalRevenue", "Revenue", "Net Revenue",
            "Net Sales", "Sales", "Total Net Sales", "Operating Revenue",
            "Total Net Revenue", "Gross Revenue", "RevenueFromContractWithCustomerExcludingAssessedTax",
        ])
        
        # Operating Income (Income Statement)
        op_inc = _row(fin, [
            "Operating Income", "OperatingIncome", "Operating Profit", 
            "Income From Operations", "Operating Income Loss"
        ])
        
        # EBITDA (Income Statement) - direct lookup first, derive if missing
        ebitda = _row(fin, [
            "EBITDA", "Ebitda",
        ])

        # Operating income, normalized EBITDA, pretax income and net interest
        # income are different concepts. Do not silently substitute them.
        da = _row(fin, ["Depreciation And Amortization", "DepreciationAndAmortization"])
        if not _exists(da):
            da = _row(cf, ["Depreciation And Amortization", "DepreciationAndAmortization"])
        if not _exists(ebitda):
            ebit = _row(fin, ["EBIT", "Ebit"])
            if _exists(ebit) and _exists(da):
                ebitda = (ebit + da).sort_index()

        if not _exists(ebitda):
            # Method 2: Net Income + Interest + Taxes + D&A
            net_inc = _row(fin, ["Net Income", "NetIncome"])
            interest = _row(fin, ["Interest Expense", "InterestExpense"])
            taxes = _row(fin, ["Income Tax Expense", "Tax Provision", "TaxProvision"])
            if all(_exists(part) for part in [net_inc, interest, taxes, da]):
                # Preserve reported signs, including tax benefits, and require
                # every component for each date. Missing is not zero.
                ebitda = pd.concat([net_inc, interest, taxes, da], axis=1).sum(axis=1, min_count=4).sort_index()

        # Operating Cash Flow (Cash Flow Statement)
        ocf = _row(cf, [
            "Operating Cash Flow", "Total Cash From Operating Activities",
            "CashFromOperatingActivities", "Net Cash From Operating Activities"
        ])

        # Capital Expenditures (Cash Flow Statement) - expanded aliases
        capex = _row(cf, [
            "Capital Expenditures", "Purchase Of PPE",
            "PurchaseOfPPE", "Capital Expenditure", "Capex", "PPE Purchase",
            "Purchase Of Property Plant Equipment", "Acquisition Of PPE",
            "Additions To Property Plant Equipment", "Investment In Property Plant Equipment",
            "Acquisition Of Property Plant Equipment", "PP&E Investment",
            "PaymentsToAcquirePropertyPlantAndEquipment",
        ])

        # FCF is unavailable unless both operating cash flow and CapEx exist.
        fcf = pd.Series(dtype="float64")
        if _exists(ocf) and _exists(capex):
            fcf = (ocf - capex.abs()).sort_index()

        # Total Debt (Balance Sheet)
        total_debt = _row(bs, ["Total Debt", "TotalDebt"])
        if not _exists(total_debt):
            # Fallback: Sum of short-term and long-term debt
            short_lt = _row(bs, ["Short Long Term Debt", "ShortLongTermDebt"])
            long_t = _row(bs, ["Long Term Debt", "LongTermDebt", "Long Term Debt Total"])
            if _exists(short_lt) and _exists(long_t):
                total_debt = (short_lt + long_t).sort_index()
                LOG.debug("[fund] Debt calculated for %s using short + long term", ticker)
            else:
                LOG.debug("[fund] No debt data for %s", ticker)

        # Cash & Cash Equivalents (Balance Sheet) - Expanded aliases
        cash = _row(bs, [
            "Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash",
            "Cash Equivalents"
        ])

        # Short Term Investments (Balance Sheet)
        sti = _row(bs, [
            "Short Term Investments", "ShortTermInvestments", 
            "Marketable Securities", "Short Term Marketable Securities"
        ])

        # Cash total calculation with fallback
        cash_and_sti = _row(bs, ["Cash Cash Equivalents And Short Term Investments", "CashAndShortTermInvestments"])
        if not _exists(cash_and_sti) and _exists(cash):
            if _exists(sti):
                cash_and_sti = (cash + sti).sort_index()
                LOG.debug("[fund] Cash total for %s: cash + short term investments", ticker)
            else:
                cash_and_sti = cash.copy()
                LOG.debug("[fund] Cash total for %s: cash only (no STI)", ticker)
        if not _exists(cash_and_sti):
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

def compute_ttm_metrics(ticker: str, quarterlies=None, annuals=None) -> FundamentalsTTM:
    """Calculate only comparable periods, preserving unknowns and provenance."""
    q = fetch_quarterlies(ticker) if quarterlies is None else quarterlies
    a = fetch_annuals(ticker) if annuals is None else annuals
    flow_keys = ("revenue", "op_inc", "fcf", "ebitda")
    latest_ends = [q[key].index.max() for key in flow_keys if _exists(q[key])]
    period_end = max(latest_ends) if latest_ends else None
    windows = {}
    for key in flow_keys:
        window = _window(q[key], 4)
        # Do not compare stale financial components against newer revenue.
        if _exists(window) and window.index[-1] == period_end:
            windows[key] = window

    result = {
        "ticker": ticker.upper(),
        "insufficient_data": not all(key in windows for key in ("revenue", "op_inc")),
        "growth_metadata": {},
        "period_metadata": {},
    }
    field_names = {
        "revenue": "revenue_ttm", "op_inc": "operating_income_ttm",
        "fcf": "fcf_ttm", "ebitda": "ebitda_ttm",
    }
    for key, window in windows.items():
        field = field_names[key]
        result[field] = float(window.sum())
        result["period_metadata"][field] = {
            "basis": "ttm", "quarter_ends": [date.date().isoformat() for date in window.index],
            "period_end": window.index[-1].date().isoformat(),
        }

    for key, field in (("revenue", "revenue_growth_yoy"), ("op_inc", "operating_income_growth_yoy"),
                       ("fcf", "fcf_growth_yoy"), ("ebitda", "ebitda_growth_yoy")):
        growth, metadata = _growth_with_basis(q[key], a.get(key, pd.Series(dtype="float64")))
        result["growth_metadata"][field] = metadata
        if growth is not None:
            result[field] = growth

    revenue = windows.get("revenue")
    for key, field in (("op_inc", "operating_margin_ttm"), ("fcf", "fcf_margin_ttm")):
        numerator = windows.get(key)
        if numerator is not None and revenue is not None and numerator.index.equals(revenue.index) and revenue.sum() != 0:
            result[field] = float(numerator.sum() / revenue.sum())

    income_years, revenue_years = _window(q["op_inc"], 8), _window(q["revenue"], 8)
    if (_exists(income_years) and _exists(revenue_years) and income_years.index.equals(revenue_years.index)
            and revenue_years.index[-1] == period_end
            and revenue_years.iloc[-4:].sum() != 0 and revenue_years.iloc[:4].sum() != 0):
        result["margin_growth_yoy_pp"] = float((income_years.iloc[-4:].sum() / revenue_years.iloc[-4:].sum()
                                               - income_years.iloc[:4].sum() / revenue_years.iloc[:4].sum()) * 100)

    debt, cash = q["debt"], q["cash_and_sti"]
    total_debt, cash_eq = _latest(debt), _latest(cash)
    if total_debt is not None:
        result["total_debt"] = total_debt
        result["period_metadata"]["total_debt"] = {
            "basis": "balance_sheet", "period_end": debt.index[-1].date().isoformat(),
        }
    if cash_eq is not None:
        result["cash_and_equivalents"] = cash_eq
        result["period_metadata"]["cash_and_equivalents"] = {
            "basis": "balance_sheet", "period_end": cash.index[-1].date().isoformat(),
        }
    # Balance-sheet ratios require the same reporting date and nonmissing latest values.
    if (_exists(debt) and _exists(cash) and debt.index[-1] == cash.index[-1]
            and pd.notna(debt.iloc[-1]) and pd.notna(cash.iloc[-1])):
        result["net_debt"] = float(debt.iloc[-1] - cash.iloc[-1])
        result["period_metadata"]["net_debt"] = {
            "basis": "balance_sheet", "period_end": debt.index[-1].date().isoformat(),
        }
        if cash.iloc[-1] != 0:
            result["debt_to_cash"] = float(debt.iloc[-1] / cash.iloc[-1])
            result["period_metadata"]["debt_to_cash"] = dict(result["period_metadata"]["net_debt"])
    return FundamentalsTTM(**result)


def compute_quarterly_series(ticker: str, quarterlies=None):
    """Return chronological series; valid zero values are observations."""
    q = fetch_quarterlies(ticker) if quarterlies is None else quarterlies
    sources = {
        "revenue_q": q["revenue"], "operating_income_q": q["op_inc"],
        "fcf_q": q["fcf"], "ebitda_q": q["ebitda"],
        "operating_margin_q": _margin_series(q["op_inc"], q["revenue"]),
        "fcf_margin_q": _margin_series(q["fcf"], q["revenue"]),
    }
    result = {}
    for name, series in sources.items():
        if _exists(series):
            result[name] = [
                FundamentalPoint(date=date.to_pydatetime(), value=float(value) if pd.notna(value) and math.isfinite(value) else None)
                for date, value in series.sort_index().items()
            ]
    return FundamentalsSeries(**result)

# Simple service wrapper to match your debug script calls
class FundamentalsService:
    def get_fundamentals_data(self, ticker: str) -> dict:
        """Get comprehensive fundamentals data with compact response."""
        try:
            q = fetch_quarterlies(ticker)
            ttm = compute_ttm_metrics(ticker, quarterlies=q)
            series = compute_quarterly_series(ticker, quarterlies=q)
            
            # Convert to dict and compact (remove None values)
            ttm_dict = ttm.model_dump(exclude_none=True) if hasattr(ttm, 'model_dump') else ttm.__dict__
            series_dict = series.model_dump(exclude_none=True) if hasattr(series, 'model_dump') else series.__dict__
            
            ttm_out = compact(ttm_dict)
            series_out = compact(series_dict)
            
            metadata = {
                "data_type": "quarterly",
                "periods_available": int(q["revenue"].shape[0]) if _exists(q["revenue"]) else 0,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source": "Yahoo Finance via yfinance",
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
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "source": "Yahoo Finance via yfinance",
                    "insufficient_data": True,
                }
            }

_service = FundamentalsService()
def get_service() -> FundamentalsService:
    return _service
