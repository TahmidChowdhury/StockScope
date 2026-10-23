"""Numerical saved-curve fixtures; no provider access or persisted experiments."""
import copy
import importlib.util
import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, stdev

import pytest

from backend.trading import risk


@pytest.fixture
def quantstats():
    if importlib.util.find_spec('quantstats') is None:
        pytest.skip('Saved-curve analytics dependency is not installed')
    _, qs = risk._library()
    return qs


def document(returns, benchmark_returns=None, days=None):
    benchmark_returns = returns if benchmark_returns is None else benchmark_returns
    days = days or [(date(2025, 1, 2) + timedelta(days=i)).isoformat() for i in range(len(returns))]
    equity = benchmark = 100.0
    curve = []
    for day, value, reference in zip(days, returns, benchmark_returns):
        equity *= 1 + value
        benchmark *= 1 + reference
        curve.append({'date': day, 'equity': equity, 'benchmark': benchmark, 'cash': 0})
    return {'id': 'run-fixture', 'kind': 'run', 'initial_cash': 100.0, 'result': {'curve': curve}}


def test_sample_estimators_include_initial_cash_and_use_quantstats(quantstats, monkeypatch):
    returns = [.10, -.05, .02, -.01]
    reference = [.05, -.025, .01, -.005]
    saved = document(returns, reference)
    before = copy.deepcopy(saved)
    calls = []
    for name in ['sharpe', 'sortino', 'volatility']:
        original = getattr(quantstats.stats, name)
        def tracked(*args, _name=name, _original=original, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)
        monkeypatch.setattr(quantstats.stats, name, tracked)
    report = risk.analyze(saved)
    metrics = report['metrics']
    assert metrics['sharpe'] == pytest.approx(mean(returns) / stdev(returns) * math.sqrt(252))
    assert metrics['sortino'] == pytest.approx(.015 / math.sqrt((.05 ** 2 + .01 ** 2) / 4) * math.sqrt(252))
    assert metrics['annualized_volatility'] == pytest.approx(stdev(returns) * math.sqrt(252))
    assert metrics['beta'] == pytest.approx(2)
    assert calls == ['sharpe', 'volatility', 'sortino']
    assert report['sample_count'] == 4  # Includes cash -> first saved close, not only close-to-close.
    assert report['coverage']['return_periods'] == report['coverage']['curve_points'] == 4
    assert report['coverage']['at_least_252_return_periods'] is False
    assert report['method']['annual_risk_free_rate'] == 0
    assert report['method']['std_ddof'] == 1
    assert report['method']['library_version'] == quantstats.__version__
    assert saved == before
    json.dumps(report, allow_nan=False)


def test_large_positive_daily_returns_are_not_misinterpreted_as_prices(quantstats):
    returns = [2.0, 3.0, 1.5]
    report = risk.analyze(document(returns))
    assert report['metrics']['sharpe'] == pytest.approx(mean(returns) / stdev(returns) * math.sqrt(252))
    assert report['metrics']['annualized_volatility'] == pytest.approx(stdev(returns) * math.sqrt(252))
    assert report['metrics']['sortino'] is None  # There is no observed downside denominator.
    assert report['metrics']['beta'] == pytest.approx(1)


def test_zero_and_insufficient_variance_return_null_not_infinity(quantstats):
    report = risk.analyze(document([0, 0, 0], [.1, -.1, .05]))
    assert report['metrics']['sharpe'] is None
    assert report['metrics']['sortino'] is None
    assert report['metrics']['annualized_volatility'] == 0
    assert report['metrics']['beta'] == 0  # Measurable covariance against a varying benchmark.
    assert risk.analyze(document([.1, -.1, .05], [0, 0, 0]))['metrics']['beta'] is None
    constant_losses = risk.analyze(document([-.1, -.1, -.1]))
    assert constant_losses['metrics']['sortino'] == pytest.approx(-math.sqrt(252))
    for values in [[], [.1]]:
        short = risk.analyze(document(values))
        for key in ['sharpe', 'sortino', 'annualized_volatility', 'beta']:
            assert short['metrics'][key] is None
        assert short['sample_count'] == len(values)
        json.dumps(short, allow_nan=False)


def test_drawdown_duration_counts_underwater_sessions_and_calendar_gaps(quantstats):
    days = ['2025-01-02', '2025-01-03', '2025-01-06', '2025-01-07']
    recovered = risk.analyze(document([0, -.1, -1 / 9, .25], days=days))
    assert recovered['metrics']['max_drawdown_duration_sessions'] == 2
    assert recovered['metrics']['max_drawdown_duration_calendar_days'] == 4
    assert recovered['coverage']['drawdown_ongoing'] is False
    ongoing = risk.analyze(document([0, -.1, -1 / 9], days=days[:3]))
    assert ongoing['coverage']['drawdown_ongoing'] is True
    assert ongoing['as_of'] == '2025-01-06'
    first_loss = risk.analyze(document([-.1, -1 / 9], days=days[:2]))
    assert first_loss['metrics']['max_drawdown_duration_sessions'] == 2
    assert first_loss['metrics']['max_drawdown_duration_calendar_days'] == 2


@pytest.mark.parametrize('bad_value', [None, '100', True, -1, float('nan'), float('inf')])
def test_invalid_saved_observations_are_rejected_without_dropping_or_filling(bad_value):
    saved = document([.1, -.1])
    saved['result']['curve'][0]['equity'] = bad_value
    with pytest.raises(ValueError, match='invalid dates or values'):
        risk.analyze(saved)


def test_duplicate_reversed_dates_and_zero_denominators_are_rejected():
    for days in [['2025-01-03', '2025-01-03'], ['2025-01-03', '2025-01-02']]:
        with pytest.raises(ValueError, match='unique and increasing'):
            risk.analyze(document([.1, -.1], days=days))
    with pytest.raises(ValueError, match='zero-equity denominator'):
        risk.analyze(document([-1, 0]))
    overflowing = document([0, 0])
    overflowing['result']['curve'][0]['equity'] = 1e-308
    overflowing['result']['curve'][1]['equity'] = 1e308
    with pytest.raises(ValueError, match='non-finite daily returns'):
        risk.analyze(overflowing)


def test_missing_quantstats_raises_a_feature_error_without_app_import_failure(monkeypatch):
    monkeypatch.delenv('MPLCONFIGDIR', raising=False)
    monkeypatch.setitem(sys.modules, 'quantstats', None)
    with pytest.raises(risk.RiskUnavailable, match='QuantStats dependency'):
        risk._library()
    assert os.environ['MPLCONFIGDIR'] == str(Path(__file__).resolve().parents[2] / '.cache' / 'matplotlib')


def test_matplotlib_cache_respects_explicit_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('MPLCONFIGDIR', str(tmp_path))
    monkeypatch.setitem(sys.modules, 'quantstats', None)
    with pytest.raises(risk.RiskUnavailable):
        risk._library()
    assert os.environ['MPLCONFIGDIR'] == str(tmp_path)
