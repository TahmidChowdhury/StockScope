"""A shared snapshot of regular-session moves for the research desk."""
import asyncio
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import exchange_calendars

from backend.core import market_provider
from backend.core.provider_cache import ProviderUnavailable, fetch_snapshot, snapshot_key
from backend.core.resources import BudgetExceeded, read_states
from backend.db.repository import SHARED_COMPANIES
from backend.services.research import parse_timestamp

SYMBOLS = ("QQQ", "SPY", "DIA", *SHARED_COMPANIES)
_NAMESPACE = "yahoo-market-tape-v1"
_KEY = snapshot_key(_NAMESPACE, SYMBOLS)
_INTERVAL = 300
_EASTERN = ZoneInfo("America/New_York")
logger = logging.getLogger(__name__)


def refresh_delay(now):
    calendar = exchange_calendars.get_calendar("XNYS")
    session = calendar.date_to_session(now.astimezone(_EASTERN).date(), direction="next")
    opening = calendar.session_open(session)
    # Allow delayed regular-session closes to arrive on half days as well.
    final_check = calendar.session_close(session) + timedelta(minutes=20)
    if now < opening:
        return (opening - now).total_seconds()
    if now < final_check:
        return min(_INTERVAL, (final_check - now).total_seconds())
    return (calendar.session_open(calendar.next_session(session)) - now).total_seconds()


def _quote(symbol, info):
    change = info.get("regularMarketChangePercent")
    if type(change) not in (float, int) or not math.isfinite(change):
        return None
    timestamp = parse_timestamp(info.get("regularMarketTime"))
    if timestamp is None or timestamp.timestamp() <= 0:
        return None
    return {"symbol": symbol, "change": change, "as_of": timestamp.isoformat()}


def saved_quotes():
    rows = read_states([_KEY]).get(_KEY, {}).get("data")
    if rows:
        return rows
    # Existing workspaces may already have dated quotes before their first batch.
    keys = {symbol: snapshot_key("yahoo-info-v1", symbol) for symbol in SYMBOLS}
    profiles = read_states(list(keys.values()))
    return [row for symbol, key in keys.items()
            if (row := _quote(symbol, profiles.get(key, {}).get("data") or {}))]


def _load():
    rows = {row["symbol"]: row for row in saved_quotes()}
    updated = False
    for info in market_provider.get_quote_batch(SYMBOLS):
        symbol = info.get("symbol")
        if symbol in SYMBOLS:
            quote = _quote(symbol, info)
            if quote and (symbol not in rows or quote["as_of"] >= rows[symbol]["as_of"]):
                rows[symbol] = quote
                updated = True
    if not updated:
        raise ProviderUnavailable("No dated market changes were available.")
    return [rows[symbol] for symbol in SYMBOLS if symbol in rows]


def refresh():
    ttl = refresh_delay(datetime.now(timezone.utc))
    return fetch_snapshot(_NAMESPACE, SYMBOLS, _load, ttl=ttl)


async def run_scheduler(stop, ready):
    while not stop.is_set():
        delay = _INTERVAL
        try:
            snapshot = await asyncio.to_thread(refresh)
            if not snapshot.stale:
                delay = max(1, snapshot.expires_at - time.time())
        except BudgetExceeded as exc:
            delay = exc.retry_after
        except Exception as exc:
            logger.warning("Market tape refresh failed (%s)", type(exc).__name__)
        finally:
            ready.set()
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
