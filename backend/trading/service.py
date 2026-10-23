from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.trading import market, storage
from backend.trading.engine import ASSUMPTIONS, simulate
from backend.trading.models import BacktestInput


class Conflict(ValueError):
    pass


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def get_document(key):
    document = storage.read(key)
    if document is None:
        raise KeyError(key)
    return document


def create_portfolio(request):
    key = f"portfolio-{uuid4()}"
    document = {**request.model_dump(mode="json"), "id": key, "kind": "portfolio", "created_at": timestamp(),
                "revision": 1, "orders": [], "data": {}, "result": None}
    return storage.mutate(key, lambda _: document)


def public_portfolio(document):
    return {k: v for k, v in document.items() if k != "data"}


def place_order(key, request):
    def update(document):
        if document is None:
            raise KeyError(key)
        existing = next((o for o in document["orders"] if o["client_order_id"] == request.client_order_id), None)
        if existing:
            if any(existing[k] != v for k, v in request.model_dump().items()):
                raise Conflict("Order ID already used with different instructions")
            return document
        if len(document["orders"]) >= 1000:
            raise ValueError("This portfolio supports at most 1,000 journal orders")
        symbols = {o["symbol"] for o in document["orders"] if not o.get("cancelled_at")} | {request.symbol}
        if len(symbols) > 20:
            raise ValueError("At most 20 symbols per paper portfolio")
        submitted = datetime.now(timezone.utc)
        document["orders"].append({**request.model_dump(), "id": str(uuid4()), "submitted_at": submitted.isoformat(),
                                   "signal_date": submitted.astimezone(market.NY).date().isoformat()})
        document["revision"] += 1
        return document
    return public_portfolio(storage.mutate(key, update))


def refresh_portfolio(key):
    document = get_document(key)
    expected = document["revision"]
    start = datetime.fromisoformat(document["created_at"]).astimezone(market.NY).date() + timedelta(days=1)
    end = market.market_today() - timedelta(days=1)
    if start > end:
        return public_portfolio(document)
    active_orders = [o for o in document["orders"] if not o.get("cancelled_at")]
    symbols = sorted({o["symbol"] for o in active_orders})
    fetched = market.fetch_bars([*symbols, document["benchmark"]], start, end)
    # Freeze each observed daily bar. Future refreshes append, never rewrite a simulated fill.
    data = copy.deepcopy(document["data"])
    for symbol, rows in fetched.items():
        saved = {r["date"]: r for r in data.get(symbol, [])}
        for row in rows:
            saved.setdefault(row["date"], row)
        data[symbol] = sorted(saved.values(), key=lambda r: r["date"])
    if not data.get(document["benchmark"]):
        return public_portfolio(document)
    result = simulate(data=data, start=start.isoformat(), end=end.isoformat(), initial_cash=document["initial_cash"],
                      benchmark=document["benchmark"], costs=document["costs"], symbols=symbols,
                      signals=active_orders)
    def update(current):
        if current["revision"] != expected:
            raise Conflict("Portfolio changed during refresh. Refresh again to include the new orders.")
        current.update(data=data, result=result, refreshed_at=timestamp(), revision=expected + 1)
        return current
    return public_portfolio(storage.mutate(key, update))


def cancel_order(key, order_id):
    def update(document):
        if document is None:
            raise KeyError(key)
        order = next((o for o in document["orders"] if o["id"] == order_id), None)
        if order is None:
            raise KeyError(order_id)
        if order.get("cancelled_at"):
            return document
        # Before the first eligible day there can be no fill, even if snapshots are stale.
        if order["signal_date"] < market.market_today().isoformat():
            raise Conflict("Only same-day queued orders can be cancelled; older orders must be evaluated by refresh")
        order["cancelled_at"] = timestamp()
        document["revision"] += 1
        return document
    return public_portfolio(storage.mutate(key, update))


def rename_backtest(key, request):
    def update(document):
        if document is None or document.get("kind") != "run":
            raise KeyError(key)
        document["name"] = request.name
        return document
    return storage.mutate(key, update)


def run_backtest(request: BacktestInput):
    disclosures, signals, exclusions = [], [], []
    symbols = request.symbols
    if request.strategy == "congress":
        document = storage.read("congress") or {"records": []}
        for row in document["records"]:
            if row["member"] != request.member:
                continue
            available = datetime.fromisoformat(row["available_date"]).date()
            signal_date = available + timedelta(days=request.disclosure_delay_days)
            # Do not invent existing holdings from disclosures before the selected window.
            if available < request.start or available > request.end:
                continue
            if row["asset_type"] not in {"stock", "etf"}:
                exclusions.append({"disclosure_id": row["disclosure_id"], "reason": "Only stocks and ETFs can be copied"})
                continue
            disclosures.append(row)
            signals.append({"id": row["disclosure_id"], "symbol": row["symbol"], "side": row["side"],
                            "signal_date": signal_date.isoformat(), "budget": request.initial_cash * request.trade_fraction,
                            "max_weight": request.max_weight, "source_url": row["source_url"], "owner": row["owner"],
                            "transaction_date": row["transaction_date"], "available_date": row["available_date"]})
        if not signals:
            raise ValueError("No eligible stock/ETF disclosures for this member within the selected date range")
        if len(signals) > 1000:
            raise ValueError("Limit a Congress test to 1,000 eligible disclosures")
        symbols = sorted({s["symbol"] for s in signals})
        if len(symbols) > 20:
            raise ValueError("Congress test spans more than 20 symbols; shorten the date range")
    data = market.prepare_data(request, symbols)
    result = simulate(data=data, start=request.start.isoformat(), end=request.end.isoformat(),
                      initial_cash=request.initial_cash, benchmark=request.benchmark, costs=request.costs,
                      symbols=symbols, strategy=request.strategy, signals=signals,
                      fast_window=request.fast_window, slow_window=request.slow_window)
    result["exclusions"] = exclusions
    if request.strategy == "congress":
        result["assumptions"] = [*ASSUMPTIONS,
            "Imported disclosure dates are user-supplied, not independently verified; filing date may differ from public availability.",
            "Start with cash and use only disclosures first public inside the window. Buy a fixed fraction of starting cash, capped by cash and the configured symbol weight; sell the entire copied symbol on a sale disclosure.",
            "Amount ranges, partial-sale amounts, options, pre-window holdings, and amendments are not replicated. Household owners are pooled for the selected member.",
            "Selecting a famous or historically successful member introduces selection bias. Test a separate unseen period and additional disclosure delays before drawing conclusions."]
    document = {"id": f"run-{uuid4()}", "kind": "run", "created_at": timestamp(),
                **request.model_dump(mode="json"), "result": result, "data": data,
                "disclosures": disclosures, "resolved_symbols": symbols, "engine_version": "daily-v1",
                "source": "Yahoo Finance via yfinance",
                "data_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()}
    return storage.mutate(document["id"], lambda _: document)
