"""Daily USD equity data. Never silently forward-fill missing observations."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def market_today():
    return datetime.now(NY).date()


def fetch_bars(symbols, start: date, end: date):
    """Reconstruct as-traded prices from Yahoo's split-adjusted historical OHLC.

    Fetch through today so splits AFTER a test's end can also be reversed.
    Yahoo dividends are expressed on the same split-adjusted share basis.
    Corporate-action observations remain provider data, not audited records.
    """
    import yfinance as yf
    output = {}
    for symbol in sorted(set(symbols)):
        try:
            ticker = yf.Ticker(symbol)
            frame = ticker.history(start=start.isoformat(), end=market_today().isoformat(),
                                   auto_adjust=False, actions=True, repair=False, timeout=12,
                                   raise_errors=True)
            metadata = ticker.history_metadata
            if metadata.get("currency") != "USD" or metadata.get("instrumentType") not in {"EQUITY", "ETF"}:
                raise ValueError("Only USD equities and ETFs are supported")
            if frame.empty:
                # A weekend-only paper refresh can have no eligible observations.
                output[symbol] = []
                continue
            bars, factor = [], 1.0
            for index, row in frame.iloc[::-1].iterrows():
                day = index.date()
                split = float(row.get("Stock Splits", 0))
                dividend = float(row.get("Dividends", 0))
                open_price, close_price = float(row["Open"]) * factor, float(row["Close"]) * factor
                if start <= day <= end:
                    if not all(math.isfinite(n) for n in (open_price, close_price, dividend, split)) or min(open_price, close_price) <= 0 or min(dividend, split) < 0:
                        raise ValueError(f"Invalid price/action on {day}")
                    bars.append({"date": day.isoformat(), "open": open_price, "close": close_price,
                                 "dividend": dividend * factor, "split": split or 1.0})
                if split:
                    factor *= split
            output[symbol] = list(reversed(bars))
        except Exception as exc:
            # Do not expose vendor responses or credentials through API errors.
            raise ValueError(f"Usable USD price history unavailable for {symbol}; no test was saved") from exc
    return output


def prepare_data(request, symbols):
    warmup = request.slow_window * 3 + 30 if request.strategy == "sma" else 0
    return fetch_bars([*symbols, request.benchmark], request.start - timedelta(days=warmup), request.end)
