"""Shared fundamentals cache: coalesced fetches, durable last-good data, no polling."""
from cachetools import TTLCache
from functools import wraps
from threading import RLock
from time import time
import copy
import hashlib
import json
from typing import Any, Callable, TypeVar

_cache_lock = RLock()
_fundamentals_cache = TTLCache(maxsize=600, ttl=6 * 3600)
F = TypeVar('F', bound=Callable[..., Any])


def cache_key(*args, **kwargs):
    return hashlib.sha256(json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str).encode()).hexdigest()


def _key(name, args, kwargs):
    return f'cache:{name}:{cache_key(*args, **kwargs)}'


def peek_many(name, symbols):
    """One compact DB query; a screen never creates cache rows or calls providers."""
    from backend.core.resources import read_states
    keys = {_key(name, (symbol,), {}): symbol for symbol in symbols}
    stored = read_states(list(keys))
    result = {keys[key]: value['result'] for key, value in stored.items() if value.get('result') is not None}
    with _cache_lock:
        result.update({symbol: copy.deepcopy(_fundamentals_cache[key][1]) for key, symbol in keys.items() if key in _fundamentals_cache})
    return result


def cached(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        from backend.core.provider_cache import fetch_snapshot
        key = _key(func.__name__, args, kwargs)
        with _cache_lock:
            entry = _fundamentals_cache.get(key)
            if entry and entry[0] > time():
                return copy.deepcopy(entry[1])

        def usable(result):
            return not (result.get('insufficient_data', result.get('metadata', {}).get('insufficient_data', False)) if isinstance(result, dict) else False)

        def load():
            return json.loads(json.dumps(func(*args, **kwargs), default=lambda value: value.isoformat(), allow_nan=False))

        saved = fetch_snapshot('fundamentals', None, load, ttl=6 * 3600,
                               storage_key=key, value_field='result', usable=usable)
        result = copy.deepcopy(saved.data)
        if saved.stale and isinstance(result, dict):
            result.setdefault('metadata', {})['stale'] = True
        elif saved.expires_at > time():
            with _cache_lock:
                _fundamentals_cache[key] = (saved.expires_at, result)
        return copy.deepcopy(result)
    return wrapper


def clear_cache():
    with _cache_lock:
        _fundamentals_cache.clear()


def cache_stats():
    with _cache_lock:
        return {'size': len(_fundamentals_cache), 'maxsize': _fundamentals_cache.maxsize, 'ttl': _fundamentals_cache.ttl}
