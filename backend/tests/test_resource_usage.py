"""Usage accounting stays durable and never logs provider credentials."""
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest

from backend.core import resources


@pytest.fixture
def local_state(monkeypatch, tmp_path):
    monkeypatch.setattr(resources, 'repository', lambda: None)
    monkeypatch.setattr(resources, 'data_directory', lambda: tmp_path)


def test_history_rollover_retention_and_cooldown(local_state):
    today = datetime.now(timezone.utc).date()
    yesterday = (today - timedelta(days=1)).isoformat()
    old = (today - timedelta(days=30)).isoformat()
    with resources.state('provider:yahoo') as usage:
        usage.update(day=yesterday, count=3, operations={'history': 3}, categories={'chart': 3},
                     responses={'429': 1}, blocked_until=123, history={old: {'count': 9}})
    summary = next(row for row in resources.usage_summary() if row['provider'] == 'yahoo')
    assert summary['used'] == 0
    assert summary['blocked_until'] == 123
    assert summary['history'] == [{'day': yesterday, 'count': 3, 'operations': {'history': 3},
                                   'categories': {'chart': 3}, 'responses': {'429': 1}}]
    resources.reserve('yahoo', cooldown=0)
    assert resources.usage_summary()[0]['history'] == summary['history']
    assert resources.usage_summary()[0]['used'] == 1


def test_request_response_and_denial_logs(local_state, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger='stockscope.usage')
    with resources.provider_operation('history'):
        resources.reserve('yahoo', cooldown=0, category='chart')
        resources.record_response('yahoo', 429, {'Retry-After': '7200', 'secret': 'never-log-me'})
        with pytest.raises(resources.BudgetExceeded):
            resources.reserve('yahoo', cooldown=0)
    events = [json.loads(record.message) for record in caplog.records if record.name == 'stockscope.usage']
    assert [row['event'] for row in events] == ['provider_attempt', 'provider_response', 'provider_cooldown', 'provider_denied']
    assert events[0]['operation'] == 'history'
    assert events[0]['category'] == 'chart'
    assert 'never-log-me' not in caplog.text
    assert resources.usage_summary()[0]['used'] == 1
    assert resources.usage_summary()[0]['responses'] == {'429': 1}


def test_response_after_midnight_preserves_previous_day(local_state):
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    with resources.state('provider:yahoo') as usage:
        usage.update(day=yesterday, count=1)
    resources.record_response('yahoo', None, {})
    summary = resources.usage_summary()[0]
    assert summary['used'] == 0
    assert summary['responses'] == {'network_error': 1}
    assert summary['history'][0]['count'] == 1


def test_operators_can_still_disable_yahoo_entirely(local_state, monkeypatch):
    monkeypatch.setenv('PROVIDER_YAHOO_DAILY_LIMIT', '0')
    with pytest.raises(resources.BudgetExceeded):
        resources.require_available('yahoo')
    with pytest.raises(resources.BudgetExceeded):
        resources.reserve('yahoo', cooldown=0)


@pytest.mark.parametrize('start,end,hours', [
    ('2026-03-08T05:00:00+00:00', '2026-03-09T04:00:00+00:00', 23),
    ('2026-11-01T04:00:00+00:00', '2026-11-02T05:00:00+00:00', 25),
])
def test_reset_at_new_york_midnight_across_dst(local_state, monkeypatch, start, end, hours):
    now = datetime.fromisoformat(start).timestamp()
    midnight = datetime.fromisoformat(end).timestamp()
    monkeypatch.setattr(resources.time, 'time', lambda: now)
    actor = resources.yahoo_principal.set('friend')
    try:
        for _ in range(50):
            resources.reserve('yahoo', cooldown=0)
        with pytest.raises(resources.PersonalYahooLimit) as denied:
            resources.reserve('yahoo', cooldown=0)
        assert denied.value.retry_after == hours * 3600
        # The UTC day has already changed, but the local allowance has not.
        now = midnight - 1
        with pytest.raises(resources.PersonalYahooLimit) as denied:
            resources.reserve('yahoo', cooldown=0)
        assert denied.value.retry_after == 1
        now = midnight
        assert resources.personal_yahoo_usage('friend')['used'] == 0
        resources.reserve('yahoo', cooldown=0)
        assert resources.personal_yahoo_usage('friend')['used'] == 1
    finally:
        resources.yahoo_principal.reset(actor)


def test_concurrent_requests_compete_for_last_personal_slot(local_state):
    from concurrent.futures import ThreadPoolExecutor
    import time
    day, _ = resources._personal_window(time.time())
    with resources.state('provider:yahoo') as usage:
        usage.update(personal_day=day, personal_counts={'same-user': 49})
    def attempt(_):
        actor = resources.yahoo_principal.set('same-user')
        try:
            resources.reserve('yahoo', cooldown=0)
            return True
        except resources.PersonalYahooLimit:
            return False
        finally:
            resources.yahoo_principal.reset(actor)
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(attempt, range(12))) == 1
    assert resources.personal_yahoo_usage('same-user')['used'] == 50
