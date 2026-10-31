"""Conservative persistent request budgets shared by all friends and collectors.

One API process is supported. Budget failures stop requests; they never switch
credentials, providers, or storage to work around a provider limit.
"""
from __future__ import annotations

import copy
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

from sqlalchemy import select

from backend.db.models import ResourceState
from backend.services.research import repository, data_directory

_lock = RLock()
# Hard local ceilings, not claims about a provider's plan allowance.
DEFAULT_LIMITS = {"yahoo": 100, "sec": 200, "newsapi": 0, "google": 30,
                  "finviz": 30, "disclosures": 10, "rss": 30, "refresh": 12}


class BudgetExceeded(RuntimeError):
    pass


def provider_for(url):
    host = (urlparse(url).hostname or '').lower()
    if host.endswith('yahoo.com') or host.endswith('yahoo.net'):
        return 'yahoo'
    if host == 'sec.gov' or host.endswith('.sec.gov'):
        return 'sec'
    if host == 'newsapi.org':
        return 'newsapi'
    if host.endswith('google.com'):
        return 'google'
    if host.endswith('finviz.com'):
        return 'finviz'
    if host == 'huggingface.co' or host.endswith(('.huggingface.co', '.hf.co')) or 'github' in host or 's3.amazonaws.com' in host:
        return 'disclosures'
    return 'rss'


def daily_limit(provider):
    # Operators can lower ceilings without permitting accidental unbounded use.
    try:
        return max(0, min(DEFAULT_LIMITS[provider], int(os.getenv('PROVIDER_' + provider.upper() + '_DAILY_LIMIT', str(DEFAULT_LIMITS[provider])))))
    except ValueError:
        return DEFAULT_LIMITS[provider]


@contextmanager
def state(key):
    with _lock:
        repo = repository()
        if repo is not None:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            with repo.session_factory.begin() as session:
                insert = pg_insert if repo.engine.dialect.name == 'postgresql' else sqlite_insert
                session.execute(insert(ResourceState).values(key=key, payload={}).on_conflict_do_nothing(index_elements=['key']))
                row = session.scalar(select(ResourceState).where(ResourceState.key == key).with_for_update())
                payload = copy.deepcopy(row.payload)
                yield payload
                row.payload = payload
        else:
            import fcntl
            directory = data_directory() / 'resource-state'
            directory.mkdir(parents=True, exist_ok=True)
            # key is always an internal constant or validated symbol, never a path from a caller.
            path = directory / (key.replace(':', '-') + '.json')
            with (directory / '.lock').open('a') as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                try:
                    payload = json.loads(path.read_text()) if path.exists() else {}
                    yield payload
                    temporary = path.with_suffix('.tmp')
                    temporary.write_text(json.dumps(payload))
                    os.replace(temporary, path)
                finally:
                    fcntl.flock(handle, fcntl.LOCK_UN)


def read_states(keys):
    repo = repository()
    if repo is not None:
        with repo.session_factory() as session:
            return dict(session.execute(select(ResourceState.key, ResourceState.payload).where(ResourceState.key.in_(keys))).all())
    result = {}
    for key in keys:
        path = data_directory() / 'resource-state' / (key.replace(':', '-') + '.json')
        if path.exists():
            result[key] = json.loads(path.read_text())
    return result


def reserve(provider, *, cooldown=1.1):
    """Count every attempted request, including failures, before any network I/O."""
    wait = 0
    with state('provider:' + provider) as usage:
        now = time.time()
        day = datetime.now(timezone.utc).date().isoformat()
        if usage.get('day') != day:
            usage.update(day=day, count=0)
        if usage.get('blocked_until', 0) > now:
            raise BudgetExceeded(f'{provider} is cooling down after a provider response. Saved data remains available.')
        if usage.get('count', 0) >= daily_limit(provider):
            raise BudgetExceeded(f'{provider} daily workspace budget reached. Saved data remains available.')
        scheduled = max(now, usage.get('next_request', 0))
        wait = scheduled - now
        if wait > 30:
            raise BudgetExceeded(f'{provider} request queue is busy. Try again later.')
        usage.update(count=usage.get('count', 0) + 1, next_request=scheduled + cooldown)
    if wait:
        time.sleep(wait)
        if read_states(['provider:' + provider]).get('provider:' + provider, {}).get('blocked_until', 0) > time.time():
            raise BudgetExceeded(f'{provider} is cooling down. Saved data remains available.')


def record_response(provider, status, headers):
    if status not in (429, 403, 503):
        return
    try:
        retry = float(headers.get('Retry-After', '3600'))
    except (TypeError, ValueError):
        from email.utils import parsedate_to_datetime
        try:
            retry = parsedate_to_datetime(headers.get('Retry-After')).timestamp() - time.time()
        except Exception:
            retry = 3600
    with state('provider:' + provider) as usage:
        usage['blocked_until'] = max(usage.get('blocked_until', 0), time.time() + max(3600, retry))


def guarded_get(url, *, session=None, **kwargs):
    import requests
    provider = provider_for(url)
    reserve(provider)
    # No hidden redirect requests outside the request budget.
    kwargs['allow_redirects'] = False
    result = (session.get if session is not None else requests.get)(url, **kwargs)
    record_response(provider, result.status_code, result.headers)
    return result


def admit_refresh(symbol):
    """Six-hour per-symbol cooldown, even on failure; durable across restarts."""
    with state('provider:refresh') as usage:
        now = time.time()
        day = datetime.now(timezone.utc).date().isoformat()
        if usage.get('day') != day:
            usage.update(day=day, count=0)
        next_by_symbol = {key: value for key, value in usage.get('symbols', {}).items() if value > now}
        if symbol in next_by_symbol:
            raise BudgetExceeded('This company was already queued recently. Research can refresh once every six hours.')
        if usage.get('count', 0) >= daily_limit('refresh'):
            raise BudgetExceeded('The workspace has used its daily research refresh budget. Saved evidence remains available.')
        next_by_symbol[symbol] = now + 6 * 3600
        usage.update(count=usage.get('count', 0) + 1, symbols=next_by_symbol)


def usage_summary():
    result = []
    day = datetime.now(timezone.utc).date().isoformat()
    for provider in DEFAULT_LIMITS:
        with state('provider:' + provider) as usage:
            result.append({'provider': provider, 'used': usage.get('count', 0) if usage.get('day') == day else 0,
                           'limit': daily_limit(provider), 'blocked_until': usage.get('blocked_until')})
    return result
