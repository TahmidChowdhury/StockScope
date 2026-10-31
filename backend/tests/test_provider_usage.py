"""Offline budget/caching checks. Never use a real provider in these tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pandas as pd
import pytest

from backend.core import market_provider as market, resources
from backend.core.provider_cache import fetch_snapshot, snapshot_key, ProviderUnavailable


def test_parallel_readers_and_restart_share_one_persisted_snapshot(monkeypatch):
    calls = []
    def load():
        calls.append(True)
        time.sleep(.03)
        return {'price': 42, 'observed_at': '2020-01-01'}
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: fetch_snapshot('fixture', 'IBM', load), range(8)))
    assert len(calls) == 1
    assert all(result == results[0] for result in results)
    # A new import/function call reads durable data, with no memory cache required.
    result = fetch_snapshot('fixture', 'IBM', lambda: pytest.fail('Restart must reuse saved data'))
    assert result == results[0]
    result.data['price'] = 999
    assert fetch_snapshot('fixture', 'IBM', load).data['price'] == 42


def test_expired_snapshot_survives_quota_and_backoff_without_redating(monkeypatch):
    first = fetch_snapshot('fixture', 'IBM', lambda: {'price': 42}, ttl=-1)
    calls = []
    def denied():
        calls.append(True)
        raise resources.BudgetExceeded('Daily limit reached', 100)
    fallback = fetch_snapshot('fixture', 'IBM', denied)
    again = fetch_snapshot('fixture', 'IBM', denied)
    assert fallback.stale and again.stale
    assert first.retrieved_at == fallback.retrieved_at == again.retrieved_at
    assert len(calls) == 1
    with pytest.raises(resources.BudgetExceeded):
        fetch_snapshot('fixture', 'IBM', denied, allow_stale=False)
    assert len(calls) == 1


def test_failed_first_fetch_is_not_retried_on_every_click():
    calls = []
    def failed():
        calls.append(True)
        raise RuntimeError('Private provider diagnostics must not be persisted')
    with pytest.raises(RuntimeError):
        fetch_snapshot('fixture', 'IBM', failed)
    with pytest.raises(ProviderUnavailable):
        fetch_snapshot('fixture', 'IBM', failed)
    assert len(calls) == 1
    entry = resources.read_states([snapshot_key('fixture', 'IBM')])
    assert 'Private provider diagnostics' not in str(entry)


def test_other_process_lease_blocks_duplicate_fetch_and_expires():
    key = snapshot_key('fixture', 'IBM')
    with resources.state(key) as stored:
        stored.update(lease='another-process', lease_until=time.time() + 30)
    with pytest.raises(ProviderUnavailable):
        fetch_snapshot('fixture', 'IBM', lambda: pytest.fail('Another process is fetching'))
    with resources.state(key) as stored:
        stored['lease_until'] = time.time() - 1
    assert fetch_snapshot('fixture', 'IBM', lambda: {'price': 42}).data['price'] == 42


def test_shared_info_normalizes_symbols_and_preserves_zero_and_observation_time(monkeypatch):
    calls = []
    class Ticker:
        @property
        def info(self):
            calls.append(True)
            return {'currentPrice': 0, 'marketCap': float('nan'), 'regularMarketTime': 1234567}
    monkeypatch.setattr(market, 'Ticker', lambda symbol: Ticker())
    first = market.get_info(' ibm ')
    second = market.get_info('IBM')
    assert first == second
    assert len(calls) == 1
    assert first.data == {'currentPrice': 0, 'marketCap': None, 'regularMarketTime': 1234567}


def test_daily_bars_keep_timezone_zero_and_missing_volume_after_restart(monkeypatch):
    calls = []
    frame = pd.DataFrame({'Open': [10., 11.], 'Close': [11., 12.], 'Volume': [0., float('nan')]},
                         index=pd.date_range('2024-03-08', periods=2, tz='America/New_York', name='Date'))
    def history(**kwargs):
        calls.append(True)
        return frame
    monkeypatch.setattr(market, 'Ticker', lambda symbol: SimpleNamespace(history=history))
    first = market.get_history('IBM', period='1y', interval='1d', timeout=10)
    second = market.get_history('IBM', period='1y', interval='1d', timeout=12)
    pd.testing.assert_frame_equal(first, second)
    assert str(second.index.tz) == 'America/New_York'
    assert second['Volume'].iloc[0] == 0
    assert pd.isna(second['Volume'].iloc[1])
    assert len(calls) == 1


def test_saved_profile_available_when_budget_is_zero(monkeypatch):
    monkeypatch.setattr(market, 'Ticker', lambda _: SimpleNamespace(info={'currentPrice': 42}))
    saved = market.get_info('IBM')
    monkeypatch.setenv('PROVIDER_YAHOO_DAILY_LIMIT', '0')
    monkeypatch.setattr(market, 'Ticker', lambda _: pytest.fail('Cache hit must not call Yahoo'))
    assert market.get_info('IBM') == saved


def test_news_cache_shared_by_both_collectors(monkeypatch):
    calls = []
    class Ticker:
        @property
        def news(self):
            calls.append(True)
            return [{'title': 'Saved article', 'providerPublishTime': 1234567}]
    monkeypatch.setattr(market, 'Ticker', lambda _: Ticker())
    assert market.get_news('ibm') == market.get_news('IBM')
    assert len(calls) == 1


def test_transport_counts_auth_data_failures_and_honors_cooldown(monkeypatch):
    from curl_cffi import requests
    calls = []
    def request(self, method, url, *args, **kwargs):
        calls.append((kwargs['timeout'], kwargs['allow_redirects']))
        return SimpleNamespace(status_code=429 if len(calls) == 2 else 200, headers={'Retry-After': '3600'})
    monkeypatch.setattr(requests.Session, 'request', request)
    monkeypatch.setattr(resources.time, 'sleep', lambda _: None)
    session = market.BudgetSession()
    with resources.provider_operation('profile'):
        session.request('GET', 'https://query1.finance.yahoo.com/v1/test/getcrumb?crumb=SECRET', timeout=30)
        session.request('GET', 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/IBM')
        with pytest.raises(resources.BudgetExceeded):
            session.request('GET', 'https://query1.finance.yahoo.com/again')
    usage = resources.read_states(['provider:yahoo'])['provider:yahoo']
    assert usage['count'] == 2
    assert usage['operations'] == {'profile': 2}
    assert usage['categories'] == {'auth': 1, 'quote': 1}
    assert usage['responses'] == {'2xx': 1, '429': 1}
    assert 'SECRET' not in str(usage)
    assert calls == [(12, False), (12, False)]


def test_old_ledger_is_reported_as_unattributed_and_resets_daily():
    with resources.state('provider:yahoo') as entry:
        entry.update(day=datetime.now(timezone.utc).date().isoformat(), count=7)
    resources.reserve('yahoo', cooldown=0, category='not-a-fixed-category')
    result = next(row for row in resources.usage_summary() if row['provider'] == 'yahoo')
    assert result['unattributed'] == 7
    assert result['operations'] == {'other': 1}
    with resources.state('provider:yahoo') as entry:
        entry['day'] = '2000-01-01'
    resources.reserve('yahoo', cooldown=0)
    result = next(row for row in resources.usage_summary() if row['provider'] == 'yahoo')
    assert result['used'] == 1 and result['unattributed'] == 0


def test_valuation_reuses_fundamentals_and_profile_snapshots(monkeypatch):
    from backend.services import valuation, fundamentals
    calls = []
    def fetch(symbol):
        calls.append(symbol)
        return {'ttm': {}, 'series': {}, 'metadata': {'insufficient_data': False, 'retrieved_at': '2020-01-01'}}
    monkeypatch.setattr(fundamentals.get_service(), 'get_fundamentals_data', fetch)
    monkeypatch.setattr(market, 'Ticker', lambda _: SimpleNamespace(info={'regularMarketPrice': 42}))
    fundamentals._compute_full_cached('IBM')
    saved = market.get_info('IBM')
    result = valuation._load('IBM')
    assert calls == ['IBM']
    assert result['quote']['fetched_at'] == saved.retrieved_at


@pytest.mark.parametrize('failure', ['exception', 'incomplete'])
def test_fundamentals_preserve_last_good_data_and_back_off_durably(failure):
    from backend.core.cache import cached, clear_cache, _key
    calls = []
    @cached
    def fixture_statements(symbol):
        calls.append(True)
        if len(calls) == 1:
            return {'ttm': {'revenue_ttm': 42}, 'metadata': {'retrieved_at': '2020-01-01'}}
        if failure == 'exception':
            raise RuntimeError('provider unavailable')
        return {'ttm': {}, 'metadata': {'insufficient_data': True}}
    original = fixture_statements('IBM')
    clear_cache()
    with resources.state(_key('fixture_statements', ('IBM',), {})) as entry:
        entry['expires_at'] = 0
    stale = fixture_statements('IBM')
    clear_cache()
    again = fixture_statements('IBM')
    assert len(calls) == 2
    assert stale == again
    assert stale['metadata']['stale'] is True
    assert stale['metadata']['retrieved_at'] == original['metadata']['retrieved_at']
    assert stale['ttm']['revenue_ttm'] == 42
