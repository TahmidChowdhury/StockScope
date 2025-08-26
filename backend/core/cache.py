"""Simple TTL cache utilities for fundamentals data."""

from cachetools import TTLCache
from functools import wraps
import hashlib
import json
from typing import Any, Callable, TypeVar

# Global cache instance - 6 hour TTL for fundamentals data
_fundamentals_cache = TTLCache(maxsize=200, ttl=6 * 3600)

F = TypeVar('F', bound=Callable[..., Any])

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items()) if kwargs else {}
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()

def cached(func: F) -> F:
    """Decorator to cache function results with TTL."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
        
        if key in _fundamentals_cache:
            return _fundamentals_cache[key]
        
        result = func(*args, **kwargs)
        _fundamentals_cache[key] = result
        return result
    
    return wrapper

def clear_cache():
    """Clear all cached data."""
    _fundamentals_cache.clear()

def cache_stats() -> dict:
    """Get cache statistics."""
    return {
        'size': len(_fundamentals_cache),
        'maxsize': _fundamentals_cache.maxsize,
        'ttl': _fundamentals_cache.ttl,
        'hits': getattr(_fundamentals_cache, 'hits', 0),
        'misses': getattr(_fundamentals_cache, 'misses', 0)
    }