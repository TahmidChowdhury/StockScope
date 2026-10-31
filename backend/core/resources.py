"""Conservative persistent request budgets shared by all friends and collectors.

One API process is supported. Budget failures stop requests; they never switch
credentials, providers, or storage to work around a provider limit.
"""
from __future__ import annotations

import copy
import json
import logging
import math
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

from sqlalchemy import select

from backend.db.models import ResourceState
from backend.services.research import repository, data_directory

LOG = logging.getLogger('stockscope.usage')
_HISTORY_DAYS = 30
_DAILY_FIELDS = ('count', 'operations', 'categories', 'responses')


def usage_event(event, **fields):
    """Structured metadata only; never pass URLs, credentials or source text."""
    LOG.info(json.dumps({'event': event, 'at': datetime.now(timezone.utc).isoformat(), **fields}, sort_keys=True))


def _roll_day(usage, day):
    if usage.get('day') != day:
        history = usage.setdefault('history', {})
        if usage.get('day'):
            history[usage['day']] = {field: copy.deepcopy(usage.get(field, 0 if field == 'count' else {}))
                                     for field in _DAILY_FIELDS}
        usage.update(day=day, count=0, operations={}, categories={}, responses={})
    cutoff = (datetime.fromisoformat(day) - timedelta(days=_HISTORY_DAYS - 1)).date().isoformat()
    usage['history'] = {key: value for key, value in usage.get('history', {}).items() if cutoff <= key < day}


_lock = RLock()
_operation = ContextVar('provider_operation', default='other')
_OPERATIONS = {'profile', 'history', 'fundamentals', 'news', 'other'}
_CATEGORIES = {'auth', 'chart', 'quote', 'statements', 'news', 'other'}


@contextmanager
def provider_operation(name):
    token = _operation.set(name if name in _OPERATIONS else 'other')
    try:
        yield
    finally:
        _operation.reset(token)


def request_category(url):
    # Only fixed categories are retained: no URLs, query strings or credentials.
    path = urlparse(url).path.lower()
    if any(part in path for part in ('getcrumb', 'consent', 'collectconsent')) or (urlparse(url).hostname or '').startswith(('fc.', 'consent.')):
        return 'auth'
    if '/chart/' in path:
        return 'chart'
    if 'fundamentals-timeseries' in path:
        return 'statements'
    if '/quote' in path:
        return 'quote'
    if 'news' in path or 'ncp' in path:
        return 'news'
    return 'other'

# Hard local ceilings, not claims about a provider's plan allowance.
DEFAULT_LIMITS = {"yahoo": 100, "sec": 200, "newsapi": 0, "google": 30,
                  "finviz": 30, "disclosures": 10, "rss": 30, "refresh": 12}


class BudgetExceeded(RuntimeError):
    def __init__(self, message, retry_after=3600):
        super().__init__(message)
        self.retry_after = max(1, math.ceil(retry_after))


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


def require_available(provider):
    """Read-only preflight so SDKs cannot disguise a denied request as missing data."""
    usage = read_states(['provider:' + provider]).get('provider:' + provider, {})
    now = datetime.now(timezone.utc)
    if usage.get('blocked_until', 0) > now.timestamp():
        raise BudgetExceeded(f'{provider.title()} is cooling down after a provider response. Saved research remains available.',
                             usage['blocked_until'] - now.timestamp())
    used = usage.get('count', 0) if usage.get('day') == now.date().isoformat() else 0
    limit = daily_limit(provider)
    if used >= limit:
        reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        raise BudgetExceeded(f'Shared {provider.title()} daily limit reached ({used}/{limit}). Saved research remains available.',
                             (reset - now).total_seconds())


def reserve(provider, *, cooldown=1.1, category="other"):
    category = category if category in _CATEGORIES else 'other'
    try:
        _reserve(provider, cooldown=cooldown, category=category)
    except BudgetExceeded as exc:
        usage_event('provider_denied', provider=provider, operation=_operation.get(), category=category,
                    retry_after_seconds=exc.retry_after, reason=str(exc))
        raise
    usage_event('provider_attempt', provider=provider, operation=_operation.get(), category=category)


def _reserve(provider, *, cooldown=1.1, category="other"):
    """Count every attempted request, including failures, before any network I/O."""
    wait = 0
    with state('provider:' + provider) as usage:
        now = time.time()
        day = datetime.now(timezone.utc).date().isoformat()
        _roll_day(usage, day)
        if usage.get('blocked_until', 0) > now:
            raise BudgetExceeded(f'{provider} is cooling down after a provider response. Saved data remains available.', usage['blocked_until'] - now)
        if usage.get('count', 0) >= daily_limit(provider):
            reset = (datetime.fromtimestamp(now, timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            raise BudgetExceeded(f'Shared {provider.title()} daily limit reached ({usage.get("count", 0)}/{daily_limit(provider)}). Saved research remains available.', reset.timestamp() - now)
        scheduled = max(now, usage.get('next_request', 0))
        wait = scheduled - now
        if wait > 30:
            raise BudgetExceeded(f'{provider} request queue is busy. Try again later.')
        usage.update(count=usage.get('count', 0) + 1, next_request=scheduled + cooldown)
        for field, label in (('operations', _operation.get()), ('categories', category if category in _CATEGORIES else 'other')):
            counts = usage.setdefault(field, {})
            counts[label] = counts.get(label, 0) + 1
        usage['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
    if wait:
        time.sleep(wait)
        if read_states(['provider:' + provider]).get('provider:' + provider, {}).get('blocked_until', 0) > time.time():
            raise BudgetExceeded(f'{provider} is cooling down. Saved data remains available.')


def record_response(provider, status, headers):
    label = str(status) if status in (401, 403, 429, 503) else (f'{status // 100}xx' if isinstance(status, int) and 100 <= status < 600 else 'network_error')
    with state('provider:' + provider) as usage:
        _roll_day(usage, datetime.now(timezone.utc).date().isoformat())
        counts = usage.setdefault('responses', {})
        counts[label] = counts.get(label, 0) + 1
    usage_event('provider_response', provider=provider, operation=_operation.get(), response=label)
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
        blocked_until = usage['blocked_until']
    usage_event('provider_cooldown', provider=provider, response=label, blocked_until=blocked_until)


def guarded_get(url, *, session=None, **kwargs):
    import requests
    provider = provider_for(url)
    reserve(provider, category=request_category(url))
    # No hidden redirect requests outside the request budget.
    kwargs['allow_redirects'] = False
    try:
        result = (session.get if session is not None else requests.get)(url, **kwargs)
    except Exception:
        record_response(provider, None, {})
        raise
    record_response(provider, result.status_code, result.headers)
    return result


def admit_refresh(symbol):
    """Six-hour per-symbol cooldown, even on failure; durable across restarts."""
    with state('provider:refresh') as usage:
        now = time.time()
        day = datetime.now(timezone.utc).date().isoformat()
        _roll_day(usage, day)
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
            _roll_day(usage, day)
            result.append({'provider': provider, 'day': day, 'unit': 'jobs' if provider == 'refresh' else 'requests',
                           'history': [{'day': date, **values} for date, values in sorted(usage.get('history', {}).items(), reverse=True)],
                           'last_attempt_at': usage.get('last_attempt_at'), 'used': usage.get('count', 0) if usage.get('day') == day else 0,
                           'limit': daily_limit(provider), 'blocked_until': usage.get('blocked_until'),
                           'operations': usage.get('operations', {}) if usage.get('day') == day else {},
                           'categories': usage.get('categories', {}) if usage.get('day') == day else {},
                           'responses': usage.get('responses', {}) if usage.get('day') == day else {},
                           'unattributed': max(0, usage.get('count', 0) - sum(usage.get('operations', {}).values())) if usage.get('day') == day else 0})
    return result
