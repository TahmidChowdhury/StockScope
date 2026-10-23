"""Deterministic long-only daily execution shared by paper and historical tests."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from backend.trading.models import Costs

ASSUMPTIONS = [
    "Research simulation, not a prediction or evidence of future profits.",
    "Signals execute at the next available session open strictly after their signal date. Daily data cannot model intraday fills.",
    "USD stocks/ETFs, fractional shares, long-only, no leverage, no interest on idle cash, no taxes or market impact beyond configured slippage.",
    "Dividends accrue as cash on ex-date (payment-date timing is not modeled); splits adjust held shares before that session's open.",
    "Ending equity marks open holdings at close; hypothetical liquidation costs are not deducted. Benchmark uses the same entry costs and dividend treatment.",
    "Yahoo historical prices/actions can be revised. Current symbol selection and incomplete delisting coverage can cause survivorship bias.",
]


class Ledger:
    def __init__(self, cash, costs):
        self.cash = cash
        self.costs = Costs.model_validate(costs) if isinstance(costs, dict) else costs
        self.positions = defaultdict(float)
        self.basis = defaultdict(float)
        self.fills = []
        self.rejected = []
        self.dividends = 0.0
        self.total_costs = 0.0
        self.realized = 0.0

    def actions(self, bars):
        for symbol, shares in list(self.positions.items()):
            if shares <= 0:
                continue
            bar = bars[symbol]
            self.positions[symbol] *= bar.get("split", 1)
            income = self.positions[symbol] * bar.get("dividend", 0)
            self.cash += income
            self.dividends += income

    def equity(self, bars, field="close"):
        return self.cash + sum(shares * bars[s][field] for s, shares in self.positions.items() if shares > 0)

    def trade(self, signal, bars, day):
        symbol, side = signal["symbol"], signal["side"]
        reference = bars[symbol]["open"]
        price = reference * (1 + self.costs.impact if side == "buy" else 1 - self.costs.impact)
        if side == "buy":
            budget = min(signal["budget"], self.cash)
            if signal.get("max_weight") is not None:
                capacity = self.equity(bars, "open") * signal["max_weight"] - self.positions[symbol] * reference
                budget = min(budget, capacity)
            if budget <= self.costs.commission + 0.000001:
                self.rejected.append({**signal, "execution_date": day, "reason": "Insufficient cash or position limit"})
                return
            shares = (budget - self.costs.commission) / price
            gross = shares * price
            self.cash -= gross + self.costs.commission
            self.positions[symbol] += shares
            self.basis[symbol] += gross + self.costs.commission
            pnl = None
        else:
            shares = self.positions[symbol]
            if shares <= 0 or shares * price <= self.costs.commission:
                self.rejected.append({**signal, "execution_date": day, "reason": "No saleable position; shorts are disabled"})
                return
            gross = shares * price
            self.cash += gross - self.costs.commission
            pnl = gross - self.costs.commission - self.basis[symbol]
            self.realized += pnl
            self.positions[symbol] = 0.0
            self.basis[symbol] = 0.0
        cost = abs(price - reference) * shares + self.costs.commission
        self.total_costs += cost
        self.fills.append({**signal, "execution_date": day, "shares": shares, "price": price,
                           "reference_price": reference, "commission": self.costs.commission,
                           "cost": cost, "realized_pnl": pnl})


def metrics(curve, initial_cash, key):
    peak, drawdown = initial_cash, 0.0
    for row in curve:
        peak = max(peak, row[key])
        drawdown = min(drawdown, row[key] / peak - 1)
    end = curve[-1][key] if curve else initial_cash
    duration = (date.fromisoformat(curve[-1]["date"]) - date.fromisoformat(curve[0]["date"])).days if len(curve) > 1 else 0
    return {"ending_equity": end, "total_return": end / initial_cash - 1,
            "max_drawdown": drawdown,
            "cagr": (end / initial_cash) ** (365.25 / duration) - 1 if duration >= 365 and end > 0 else None}


def simulate(*, data, start, end, initial_cash, benchmark, costs, symbols, strategy="orders",
             signals=None, fast_window=20, slow_window=50):
    symbols = sorted(set(symbols))
    indexes = {s: {row["date"]: row for row in rows} for s, rows in data.items()}
    if benchmark not in indexes:
        raise ValueError("Benchmark history missing")
    sessions = sorted(d for d in indexes[benchmark] if start <= d <= end)
    if not sessions:
        raise ValueError("No completed benchmark sessions in this date range")
    # Price histories must cover EVERY benchmark session, not a favorable intersection.
    for symbol in symbols:
        required = sorted(d for d in indexes[benchmark] if d <= end) if strategy == "sma" else sessions
        missing = [d for d in required if d not in indexes.get(symbol, {})]
        if missing:
            raise ValueError(f"{symbol} has missing daily data on {missing[0]}; shorten the range or repair the source")
    ledger, reference = Ledger(initial_cash, costs), Ledger(initial_cash, costs)
    events, pending = defaultdict(list), []
    for signal in signals or []:
        eligible = next((d for d in sessions if d > signal["signal_date"]), None)
        if eligible:
            events[eligible].append(signal)
        else:
            pending.append(signal)
    all_symbols = set(symbols) | {benchmark}
    history = {}
    if strategy == "sma":
        symbol = symbols[0]
        # Split/dividend-adjusted history for indicators, without changing execution prices.
        rows = sorted(data[symbol], key=lambda r: r["date"])
        adjusted, factor = {}, 1.0
        for i in range(len(rows) - 1, -1, -1):
            row = rows[i]
            adjusted[row["date"]] = row["close"] / factor
            if i:
                previous = rows[i - 1]["close"] / row.get("split", 1)
                dividend = row.get("dividend", 0)
                if dividend >= previous:
                    raise ValueError("Dividend exceeds prior price; unsupported corporate action")
                factor *= row.get("split", 1) / (1 - dividend / previous)
        for day in sessions:
            history[day] = [adjusted[r["date"]] for r in rows if r["date"] < day]
        if len(history[sessions[0]]) < slow_window:
            raise ValueError("Insufficient pre-start history for the slow moving average")
    curve = []
    for i, day in enumerate(sessions):
        bars = {s: indexes[s][day] for s in all_symbols}
        ledger.actions(bars)
        reference.actions(bars)
        if i == 0:
            reference.trade({"symbol": benchmark, "side": "buy", "budget": initial_cash, "signal_date": (date.fromisoformat(start) - timedelta(days=1)).isoformat()}, bars, day)
            if strategy == "buy_hold":
                for symbol in symbols:
                    ledger.trade({"symbol": symbol, "side": "buy", "budget": initial_cash / len(symbols), "signal_date": (date.fromisoformat(start) - timedelta(days=1)).isoformat()}, bars, day)
        if strategy == "sma":
            symbol = symbols[0]
            prior = history[day]
            wants_long = mean(prior[-fast_window:]) > mean(prior[-slow_window:])
            if wants_long != (ledger.positions[symbol] > 0):
                ledger.trade({"symbol": symbol, "side": "buy" if wants_long else "sell", "budget": ledger.cash,
                              "signal_date": max(d for d in indexes[symbol] if d < day)}, bars, day)
        # Stable order defined by caller; same-day contradictory disclosures are visible in fills.
        for event in events[day]:
            ledger.trade(event, bars, day)
        curve.append({"date": day, "equity": ledger.equity(bars), "benchmark": reference.equity(bars), "cash": ledger.cash})
    strategy_metrics, benchmark_metrics = metrics(curve, initial_cash, "equity"), metrics(curve, initial_cash, "benchmark")
    last_bars = {s: indexes[s][sessions[-1]] for s in all_symbols}
    return {"metrics": {**strategy_metrics, "benchmark_return": benchmark_metrics["total_return"],
                         "excess_return": strategy_metrics["total_return"] - benchmark_metrics["total_return"],
                         "benchmark_drawdown": benchmark_metrics["max_drawdown"], "total_costs": ledger.total_costs,
                         "benchmark_costs": reference.total_costs, "dividends": ledger.dividends,
                         "realized_pnl": ledger.realized, "fill_count": len(ledger.fills)},
            "curve": curve, "fills": ledger.fills, "rejected": ledger.rejected, "pending": pending,
            "positions": [{"symbol": s, "shares": q, "cost_basis": ledger.basis[s],
                           "price": last_bars[s]["close"], "market_value": q * last_bars[s]["close"],
                           "unrealized_pnl": q * last_bars[s]["close"] - ledger.basis[s]}
                          for s, q in ledger.positions.items() if q > 0],
            "cash": ledger.cash, "as_of": sessions[-1], "assumptions": ASSUMPTIONS}
