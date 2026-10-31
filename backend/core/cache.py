"""Shared fundamentals cache: coalesced fetches, durable last-good data, no polling."""
from cachetools import TTLCache
from functools import wraps
from threading import RLock
from time import time
import hashlib
import json
from typing import Any, Callable, TypeVar

_cache_lock = RLock()
_key_locks = [RLock() for _ in range(64)]
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
        result.update({symbol: _fundamentals_cache[key] for key, symbol in keys.items() if key in _fundamentals_cache})
    return result


def cached(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        from backend.core.resources import state, read_states
        key = _key(func.__name__, args, kwargs)
        with _key_locks[int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(_key_locks)]:
            with _cache_lock:
                if key in _fundamentals_cache:
                    return _fundamentals_cache[key]
            stored = read_states([key]).get(key, {})
            previous, expires = stored.get('result'), stored.get('expires_at', 0)
            if previous is not None and expires > time():
                return previous
            result = func(*args, **kwargs)
            insufficient = result.get('insufficient_data', result.get('metadata', {}).get('insufficient_data', False)) if isinstance(result, dict) else False
            if insufficient and previous is not None:
                # Original observation/retrieval dates remain intact.
                with _cache_lock:
                    _fundamentals_cache[key] = previous
                return previous
            serializable = json.loads(json.dumps(result, default=lambda value: value.isoformat(), allow_nan=False))
            with _cache_lock:
                _fundamentals_cache[key] = serializable
            if not insufficient:
                with state(key) as stored:
                    stored.update(result=serializable, expires_at=time() + 6 * 3600)
            return serializable
    return wrapper


def clear_cache():
    with _cache_lock:
        _fundamentals_cache.clear()


def cache_stats():
    with _cache_lock:
        return {'size': len(_fundamentals_cache), 'maxsize': _fundamentals_cache.maxsize, 'ttl': _fundamentals_cache.ttl}
