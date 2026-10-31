"""Durable provider snapshots; one refresh per key, with failure backoff.

Leases prevent duplicate fetches across processes sharing the database. No DB
transaction stays open during network I/O. Original retrieval times survive
restarts and stale fallback. Keys contain hashes, never provider credentials.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock

from backend.core.resources import BudgetExceeded, PersonalYahooLimit, daily_limit, read_states, state

_locks = [RLock() for _ in range(64)]


class ProviderUnavailable(RuntimeError):
    pass


@dataclass
class Snapshot:
    data: object
    retrieved_at: str | None
    stale: bool = False
    expires_at: float = 0


def snapshot_key(namespace, identity):
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return f'provider-cache:{namespace}:{digest}'


def fetch_snapshot(namespace, identity, loader, *, ttl=3600, allow_stale=True,
                   storage_key=None, value_field='data', usable=lambda data: True):
    key = storage_key or snapshot_key(namespace, identity)

    def snapshot(entry, stale=False):
        # Fundamentals snapshots written before this cache have their original
        # retrieval date inside metadata. Never invent a date during migration.
        value = entry[value_field]
        retrieved = entry.get('retrieved_at') or (value.get('metadata', {}).get('retrieved_at') if isinstance(value, dict) else None)
        return Snapshot(value, retrieved, stale, entry.get('expires_at', 0))
    with _locks[int(key[-8:], 16) % len(_locks)]:
        stored = read_states([key]).get(key, {})
        if value_field in stored and stored.get('expires_at', 0) > time.time():
            return snapshot(stored)
        token = uuid.uuid4().hex
        with state(key) as entry:
            now = time.time()
            if value_field in entry and entry.get('expires_at', 0) > now:
                return snapshot(entry)
            # Older releases persisted the app's Yahoo daily denial until midnight.
            # Retire only that denial, preserving refresh leases and upstream cooldowns.
            legacy_yahoo_cap = (entry.get('budget_message') or '').startswith('Shared Yahoo daily limit reached (')
            if legacy_yahoo_cap and daily_limit('yahoo') is None:
                entry.update(budget_message=None, retry_at=0)
            if max(entry.get('lease_until', 0), entry.get('retry_at', 0)) > now:
                if allow_stale and value_field in entry:
                    return snapshot(entry, True)
                if entry.get('failure_result') is not None and entry.get('retry_at', 0) > now:
                    return Snapshot(entry['failure_result'], entry.get('failure_retrieved_at'), True)
                if entry.get('budget_message') and entry.get('retry_at', 0) > now:
                    raise BudgetExceeded(entry['budget_message'], entry['retry_at'] - now)
                raise ProviderUnavailable('Market data is temporarily unavailable. Please try again in a few minutes.')
            previous = dict(entry)
            # Longer than the bounded provider operation; abandoned leases expire.
            entry.update(lease=token, lease_until=now + 300)
        try:
            data = loader()
            # Reject unsupported/nonfinite payloads before replacing last-good data.
            data = json.loads(json.dumps(data, allow_nan=False))
        except Exception as error:
            with state(key) as entry:
                if entry.get('lease') == token:
                    if isinstance(error, PersonalYahooLimit):
                        # Another account may refresh this same snapshot immediately.
                        entry.update(lease_until=0, retry_at=0, budget_message=None)
                    else:
                        entry.update(lease_until=0, retry_at=time.time() + (error.retry_after if isinstance(error, BudgetExceeded) else 300),
                                     budget_message=str(error) if isinstance(error, BudgetExceeded) else None)
            if allow_stale and value_field in previous:
                return snapshot(previous, True)
            raise
        retrieved_at = datetime.now(timezone.utc).isoformat()
        if not usable(data):
            with state(key) as entry:
                if entry.get('lease') == token:
                    entry.update(failure_result=data, failure_retrieved_at=retrieved_at,
                                 lease_until=0, retry_at=time.time() + 300, budget_message=None)
            if allow_stale and value_field in previous:
                return snapshot(previous, True)
            return Snapshot(data, retrieved_at, True)
        expires_at = time.time() + ttl
        with state(key) as entry:
            if entry.get('lease') == token:
                entry[value_field] = data
                entry.update(retrieved_at=retrieved_at, expires_at=expires_at,
                             lease_until=0, retry_at=0, budget_message=None, failure_result=None)
        return Snapshot(data, retrieved_at, expires_at=expires_at)
