"""Read-only valuation evidence. No recommendation, SEC collection or database writes."""

from __future__ import annotations

import asyncio
from contextvars import copy_context
from backend.core.resources import PersonalYahooLimit, yahoo_principal
import math
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Any

from cachetools import TTLCache
import backend.core.market_provider as yf

from backend.services.fundamentals import _compute_full_cached

SOURCE = "Yahoo Finance via yfinance"
PRICE_MAX_AGE_DAYS = 4
FINANCIAL_MAX_AGE_DAYS = 200
REQUEST_TIMEOUT_SECONDS = 25
# Deliberately bounded supported ISO 4217 units. Unrecognized units remain unknown.
SUPPORTED_CURRENCIES = frozenset("USD EUR GBP JPY CNY HKD CAD AUD CHF NZD INR SGD KRW TWD BRL MXN ZAR NOK SEK DKK ILS PLN CZK HUF TRY THB MYR IDR PHP AED SAR QAR KWD BHD OMR EGP CLP COP PEN ARS VND PKR BDT LKR".split())
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="valuation")
_lock = threading.Lock()
_cache: TTLCache = TTLCache(maxsize=100, ttl=3600)
_inflight: dict[tuple, Future] = {}


class ValuationBusy(Exception):
    pass


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def currency(value: Any) -> str | None:
    # Case matters: GBp is a minor quote unit, not GBP. Never silently convert it.
    return value if isinstance(value, str) and value in SUPPORTED_CURRENCIES else None


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if isinstance(value, str) else None
    except ValueError:
        return None


def _period_status(end: Any, today: date) -> str:
    parsed = _date(end)
    if parsed is None or parsed > today:
        return "unknown"
    return "stale" if (today - parsed).days > FINANCIAL_MAX_AGE_DAYS else "available"


def _ttm_period(period: dict) -> bool:
    ends = [_date(value) for value in (period.get("quarter_ends") or [])]
    return (period.get("basis") == "ttm" and len(ends) == 4 and all(end is not None for end in ends)
            and ends[-1] == _date(period.get("period_end"))
            and all(75 <= (right - left).days <= 105 for left, right in zip(ends, ends[1:])))


def _price_timestamp(value: Any, now: datetime) -> tuple[str | None, str]:
    value = number(value)
    if value is None:
        return None, "unknown"
    try:
        timestamp = datetime.fromtimestamp(value, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None, "unknown"
    age = (now - timestamp).total_seconds()
    if age < -300:
        return timestamp.isoformat(), "unknown"
    return timestamp.isoformat(), "stale" if age > PRICE_MAX_AGE_DAYS * 86400 else "available"


def build_valuation(symbol: str, fundamentals: dict, info: dict, *, now: datetime | None = None,
                    issues: list[str] | None = None) -> dict:
    """Pure calculation boundary: explicit currency, reporting periods and missing values."""
    now = now or datetime.now(timezone.utc)
    ttm = fundamentals.get("ttm") or {}
    metadata = fundamentals.get("metadata") or {}
    periods = ttm.get("period_metadata") or {}
    growth = ttm.get("growth_metadata") or {}
    quote_currency = currency(info.get("currency"))
    # This declaration describes the provider's financial statements, not an FX conversion.
    financial_currency = currency(metadata.get("financial_currency")) or currency(info.get("financialCurrency"))
    compatible = quote_currency is not None and quote_currency == financial_currency
    price = number(info.get("regularMarketPrice"))
    price_at, quote_status = _price_timestamp(info.get("regularMarketTime"), now)
    if price is None or price <= 0:
        price, quote_status = None, "missing"
    market_cap = number(info.get("marketCap"))
    enterprise_value = number(info.get("enterpriseValue"))
    warnings = list(issues or [])
    if not compatible:
        warnings.append("Quote and financial statement currencies are unknown or different; cross-currency valuation ratios are withheld. No FX conversion is assumed.")
    if quote_status != "available":
        warnings.append("The quote is missing, has an unknown timestamp, or is older than four calendar days. Price-based valuation ratios are withheld.")
    if fundamentals.get("error"):
        warnings.append("Financial statement data could not be loaded.")

    def metric(key, label, value, fmt, *, period_end=None, basis=None, reason=None, status=None):
        value = number(value)
        state = status or ("missing" if value is None else _period_status(period_end, now.date()))
        if value is None and state == "available":
            state = "unavailable"
        return {"key": key, "label": label, "value": value, "format": fmt, "status": state,
                "reason": reason, "period_end": period_end, "basis": basis}

    quality = []
    for key, label, field in (
        ("revenue_growth", "Revenue growth", "revenue_growth_yoy"),
        ("fcf_growth", "Free cash flow growth", "fcf_growth_yoy"),
    ):
        provenance = growth.get(field) or {}
        quality.append({**metric(key, label, ttm.get(field), "percent", period_end=provenance.get("current_period_end"),
                                basis=provenance.get("basis"), reason=("Growth is undefined with a non-positive prior period." if provenance.get("status") == "non_positive_prior" else None)),
                        "prior_period_end": provenance.get("prior_period_end")})
    for key, label, field, numerator in (
        ("operating_margin", "Operating margin", "operating_margin_ttm", "operating_income_ttm"),
        ("fcf_margin", "Free cash flow margin", "fcf_margin_ttm", "fcf_ttm"),
    ):
        period = periods.get(numerator) or {}
        quality.append(metric(key, label, ttm.get(field), "percent", period_end=period.get("period_end"), basis=period.get("basis")))
    debt_period = periods.get("net_debt") or periods.get("total_debt") or {}
    quality.append(metric("debt_cash", "Debt / cash & short-term investments", ttm.get("debt_to_cash"), "multiple",
                          period_end=debt_period.get("period_end"), basis="balance_sheet",
                          reason="Balance-sheet date is unknown." if not debt_period.get("period_end") else None))

    valuation = []
    for key, label, field, denominator, fmt in (
        ("fcf_yield", "Provider FCF / market cap", "fcf_ttm", market_cap, "percent"),
        ("ev_sales", "Enterprise value / sales", "revenue_ttm", enterprise_value, "multiple"),
        ("ev_ebitda", "Enterprise value / EBITDA", "ebitda_ttm", enterprise_value, "multiple"),
    ):
        amount = number(ttm.get(field))
        period = periods.get(field) or {}
        end = period.get("period_end")
        state = _period_status(end, now.date())
        reason = None
        value = None
        if not compatible:
            reason, state = "Matching quote and financial currencies are required.", "unknown"
        elif quote_status != "available":
            reason, state = "A recent, timestamped quote is required.", quote_status
        elif not _ttm_period(period):
            reason, state = "Four consecutive quarters with a known TTM period are required.", "unknown"
        elif state != "available":
            reason = "Financial period is unknown or older than 200 calendar days."
        elif amount is None or denominator is None:
            reason, state = "A required financial or market value is unavailable.", "missing"
        elif key == "fcf_yield" and denominator <= 0:
            reason, state = "Positive market capitalization is required.", "unavailable"
        elif key != "fcf_yield" and amount <= 0:
            reason, state = "A positive sales or EBITDA denominator is required; negative amounts remain in the financials.", "unavailable"
        else:
            value = amount / denominator if key == "fcf_yield" else denominator / amount
        valuation.append(metric(key, label, value, fmt, period_end=end, basis="ttm", reason=reason, status=state))

    return {
        "symbol": symbol, "company": info.get("shortName") or info.get("longName") or symbol,
        "source": SOURCE, "fetched_at": now.isoformat(),
        "quote": {"price": price, "currency": quote_currency, "raw_currency": info.get("currency"),
                  "price_at": price_at, "status": quote_status, "market_cap": market_cap,
                  "enterprise_value": enterprise_value, "shares_outstanding": number(info.get("sharesOutstanding")),
                  "source": SOURCE, "fetched_at": now.isoformat()},
        "financials": {"currency": financial_currency, "currency_basis": "provider financialCurrency declaration" if financial_currency else "unknown",
                       "currency_compatible": compatible, "periods": periods,
                       "fetched_at": metadata.get("retrieved_at"), "source": metadata.get("source") or SOURCE,
                       "fcf_ttm": number(ttm.get("fcf_ttm")), "revenue_ttm": number(ttm.get("revenue_ttm")),
                       "ebitda_ttm": number(ttm.get("ebitda_ttm"))},
        "quality": quality, "valuation": valuation, "warnings": warnings,
        "methodology": {
            "fcf": "Provider free cash flow is operating cash flow minus the absolute value of capital expenditures. It is not verified FCFF or FCFE.",
            "ratios": "Current provider market cap and enterprise value divided by comparable TTM financials. Values may be delayed. Financial reporting dates are not publication dates.",
            "freshness": {"price_max_age_calendar_days": PRICE_MAX_AGE_DAYS, "financial_max_age_calendar_days": FINANCIAL_MAX_AGE_DAYS},
            "coverage": "No rating or buy/sell recommendation is calculated. Missing and incompatible inputs are not scored as zero.",
        },
    }


def _load(symbol: str) -> dict:
    issues = []
    try:
        fundamentals = _compute_full_cached(symbol)
        if fundamentals.get('metadata', {}).get('stale'):
            issues.append("Using saved financial statements; the provider could not be refreshed.")
    except PersonalYahooLimit:
        raise
    except Exception:
        fundamentals = {}
        issues.append("Financial statement provider is unavailable.")
    try:
        saved_info = yf.get_info(symbol)
        info = saved_info.data
        if saved_info.stale:
            issues.append("Using saved quote data; the provider could not be refreshed.")
    except PersonalYahooLimit:
        raise
    except Exception:
        info = {}
        issues.append("Quote and company profile provider is unavailable.")
    result = build_valuation(symbol, fundamentals, info, issues=issues)
    if info:
        result['quote']['fetched_at'] = saved_info.retrieved_at
    return result


def _completed(key, future: Future) -> None:
    with _lock:
        _inflight.pop(key, None)
        if not future.cancelled() and future.exception() is None:
            _cache[key] = future.result()


async def get_valuation(symbol: str) -> dict:
    """At most four actual provider jobs, including jobs outliving HTTP timeouts.

    Repeat requests by one account for the same symbol share one job. A timeout does not free a worker
    slot while its underlying provider call still runs, so slow calls cannot
    create an unbounded queue of threads or provider requests.
    """
    key = (yahoo_principal.get(), symbol)
    with _lock:
        if key in _cache:
            return _cache[key]
        future = _inflight.get(key)
        created = future is None
        if created:
            if len(_inflight) >= 4:
                raise ValuationBusy()
            future = _pool.submit(copy_context().run, _load, symbol)
            _inflight[key] = future
    # Register outside the lock: add_done_callback runs synchronously if done.
    if created:
        future.add_done_callback(lambda done: _completed(key, done))
    return await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), REQUEST_TIMEOUT_SECONDS)
