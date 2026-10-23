"""Read-only historical risk analytics over a saved experiment's daily equity curve.

QuantStats 0.0.77 supplies the annualized Sharpe, Sortino, and volatility
estimators. No library download/report helpers or market providers are used.
"""
from __future__ import annotations

import math
import os
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, stdev, variance

PERIODS_PER_YEAR = 252
ZERO_DEVIATION_TOLERANCE = 1e-14


class RiskUnavailable(RuntimeError):
    pass


def _library():
    # An analytics installation failure must not prevent research/trading routes
    # from starting. Load the optional runtime only when a risk report is asked for.
    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / ".cache" / "matplotlib"))
    try:
        import pandas as pd
        import quantstats as qs
    except (ImportError, OSError) as exc:
        raise RiskUnavailable("Saved-curve risk analytics are unavailable; install the configured QuantStats dependency") from exc
    return pd, qs


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Saved equity curve contains an invalid value; no risk report was computed")
    return float(value)


def _finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def _drawdown_duration(rows, initial_cash):
    if not rows:
        return None, None, False
    # There is no saved pre-entry closing observation. A first-session loss is
    # measured against initial cash, with a declared synthetic calendar anchor.
    peak, peak_date = initial_cash, rows[0][0] - timedelta(days=1)
    underwater_sessions, longest_sessions, longest_days = 0, 0, 0
    for day, equity, _ in rows:
        if equity >= peak:
            peak, peak_date = equity, day
            underwater_sessions = 0
        else:
            underwater_sessions += 1
            longest_sessions = max(longest_sessions, underwater_sessions)
            longest_days = max(longest_days, (day - peak_date).days)
    return longest_sessions, longest_days, underwater_sessions > 0


def analyze(document):
    """Compute a derived report without modifying document, observations, or results."""
    if document.get("kind") != "run":
        raise ValueError("Risk analytics require a saved backtest")
    initial_cash = _number(document.get("initial_cash"))
    if initial_cash <= 0:
        raise ValueError("Saved initial cash must be positive")
    result = document.get("result")
    curve = result.get("curve") if isinstance(result, dict) else None
    if not isinstance(curve, list):
        raise ValueError("Saved daily equity observations are unavailable")
    rows, returns, benchmark_returns = [], [], []
    previous_equity, previous_benchmark = initial_cash, initial_cash
    previous_date = None
    for row in curve:
        try:
            day = date.fromisoformat(row["date"])
            equity, benchmark = _number(row["equity"]), _number(row["benchmark"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Saved equity curve has invalid dates or values; observations were not filled or dropped") from exc
        if previous_date is not None and day <= previous_date:
            raise ValueError("Saved equity dates must be unique and increasing")
        if min(previous_equity, previous_benchmark) <= 0:
            raise ValueError("A saved zero-equity denominator prevents a complete return series")
        period_return, reference_return = equity / previous_equity - 1, benchmark / previous_benchmark - 1
        if not all(math.isfinite(value) for value in (period_return, reference_return)):
            raise ValueError("Saved observations produce non-finite daily returns")
        rows.append((day, equity, benchmark))
        returns.append(period_return)
        benchmark_returns.append(reference_return)
        previous_equity, previous_benchmark, previous_date = equity, benchmark, day

    pd, qs = _library()
    count = len(returns)
    sharpe = sortino = volatility = beta = None
    if count >= 2:
        series = pd.Series(returns, index=pd.to_datetime([row[0] for row in rows]), dtype=float)
        deviation = stdev(returns)
        # QuantStats infers price input for all-positive series exceeding 1.
        # Positive scaling avoids that heuristic without changing either
        # ratio at the explicitly zero risk-free rate.
        ratio_series = series / max(1.0, max(abs(value) for value in returns))
        if deviation > ZERO_DEVIATION_TOLERANCE:
            sharpe = _finite(qs.stats.sharpe(ratio_series, rf=0, periods=PERIODS_PER_YEAR, annualize=True, smart=False))
        volatility = _finite(qs.stats.volatility(series, periods=PERIODS_PER_YEAR, annualize=True, prepare_returns=False))
        downside = math.sqrt(sum(min(value, 0) ** 2 for value in returns) / count)
        if downside > ZERO_DEVIATION_TOLERANCE:
            sortino = _finite(qs.stats.sortino(ratio_series, rf=0, periods=PERIODS_PER_YEAR, annualize=True, smart=False))
        benchmark_variance = variance(benchmark_returns)
        if benchmark_variance > ZERO_DEVIATION_TOLERANCE ** 2:
            # QuantStats greeks() fills undefined beta with zero. Use the
            # explicit sample estimator here so unavailable beta remains null.
            return_mean, benchmark_mean = mean(returns), mean(benchmark_returns)
            covariance = sum((value - return_mean) * (reference - benchmark_mean)
                             for value, reference in zip(returns, benchmark_returns)) / (count - 1)
            beta = _finite(covariance / benchmark_variance)
    duration_sessions, duration_days, ongoing = _drawdown_duration(rows, initial_cash)
    return {
        "as_of": rows[-1][0].isoformat() if rows else None,
        "sample_count": count,
        "metrics": {
            "sharpe": sharpe, "sortino": sortino, "annualized_volatility": volatility, "beta": beta,
            "max_drawdown_duration_sessions": duration_sessions,
            "max_drawdown_duration_calendar_days": duration_days,
        },
        "coverage": {
            "curve_points": len(curve), "return_periods": count, "benchmark_return_periods": len(benchmark_returns),
            "first_return_includes_initial_cash": True, "drawdown_ongoing": ongoing,
            "start": rows[0][0].isoformat() if rows else None,
            "end": rows[-1][0].isoformat() if rows else None,
            "at_least_252_return_periods": count >= PERIODS_PER_YEAR,
        },
        "method": {
            "library": "quantstats", "library_version": qs.__version__, "annual_risk_free_rate": 0,
            "periods_per_year": PERIODS_PER_YEAR, "std_ddof": 1,
            "downside_denominator": "all_return_periods", "autocorrelation_adjustment": False,
            "first_period": "initial_cash_to_first_saved_close",
            "beta": "sample_covariance_divided_by_sample_benchmark_variance",
            "zero_deviation_tolerance": ZERO_DEVIATION_TOLERANCE,
            "drawdown_duration": "consecutive_underwater_saved_sessions; calendar_days_from_peak_to_last_underwater_close; recovery_excluded",
        },
        "assumptions": [
            "Historical analysis of saved daily equity observations only; no prices were fetched and the saved experiment was not changed.",
            "Samples are daily return periods, not trades. First strategy and benchmark returns include initial cash to first saved close, including entry costs and the first intraday move.",
            "Annualization uses 252 sessions, annual risk-free rate 0, arithmetic mean returns, and sample standard deviation (ddof=1); no autocorrelation adjustment.",
            "Sortino downside deviation is sqrt(sum(min(return, 0)^2) / all return periods). Positive scaling prevents library price inference without changing zero-risk-free ratios.",
            "Undefined ratios with zero denominators and fewer-than-two-period estimates are null. Observed zero volatility is retained; a cash-only strategy can have beta 0 when benchmark variance is measurable.",
            "Drawdown duration counts consecutive saved sessions below the prior peak; recovery sessions are excluded. Calendar days run from the peak to the last underwater close. For a first-session loss, initial cash is anchored one calendar day before the first close.",
            "No dates or observations are filled, dropped, or independently checked against an exchange calendar. Annualized estimates from short windows are unstable and do not predict future risk or return.",
        ],
    }
