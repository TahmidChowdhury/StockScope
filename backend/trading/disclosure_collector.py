"""Bounded disclosure ingestion with durable leases, history, and retry status.

The source snapshot is fetched outside storage transactions. A lease fences stale
workers, including workers left behind by a deployment, from committing results.
Existing manual CSV imports are kept in their separate ``congress`` document.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.trading import storage

logger = logging.getLogger(__name__)
DOCUMENT_ID = "congress-feed"
MAX_RECORDS = 50_000
LEASE_SECONDS = 15 * 60
POLL_SECONDS = 60
COLLECTOR_FIELDS = frozenset({"first_seen_at", "observed_at", "last_seen_at", "supersession_observed_at"})


class SnapshotConflict(ValueError):
    """An upstream immutable identity changed; preserve prior evidence for review."""


class SnapshotCapacity(ValueError):
    """Retaining the complete history would exceed the configured workspace limit."""


class SnapshotWithdrawal(ValueError):
    """A previously accepted version disappeared from a refreshed source year."""


def utcnow():
    return datetime.now(timezone.utc)


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def enabled():
    configured = os.getenv("DISCLOSURE_COLLECTION_ENABLED")
    return bool(os.getenv("DATABASE_URL")) if configured is None else configured.strip().lower() == "true"


def interval_seconds():
    try:
        hours = int(os.getenv("DISCLOSURE_COLLECTION_INTERVAL_HOURS", "6"))
    except ValueError:
        hours = 6
    return max(1, min(hours, 24)) * 3600


def _empty():
    return {"id": DOCUMENT_ID, "kind": "congress_feed", "revision": 0,
            "records": [], "source": {}, "collection": {}}


def status(document=None):
    """Expose collection health without source records or the private lease token."""
    document = (storage.read_summary(DOCUMENT_ID) if document is None else document) or _empty()
    collection = document.get("collection", {})
    active = enabled()
    state = collection.get("state", "idle") if active else "disabled"
    error = collection.get("last_error")
    expiry = _time(collection.get("lease_expires_at"))
    if active and state == "running" and (expiry is None or expiry <= utcnow()):
        state = "interrupted"
        error = "The previous collection did not finish. The next scheduled check will retry it."
    return {"enabled": active, "state": state,
            "last_attempt": collection.get("last_attempt"), "last_success": collection.get("last_success"),
            "next_run": collection.get("next_run") if active else None, "last_error": error,
            "source": copy.deepcopy(document.get("source", {})),
            "row_count": len(document["records"]) if "records" in document else document.get("row_count", 0),
            "counts": copy.deepcopy(collection.get("counts", {})),
            "interval_hours": interval_seconds() // 3600, "data_revision": document.get("revision", 0)}


def _claim(document, token, now, force):
    document = document or _empty()
    collection = document.setdefault("collection", {})
    expiry = _time(collection.get("lease_expires_at"))
    if collection.get("lease_token") and expiry is not None and expiry > now:
        return document
    due = _time(collection.get("next_run"))
    if not force and due is not None and due > now:
        return document
    collection.update(state="running", last_attempt=now.isoformat(), last_error=None,
                      lease_token=token, lease_expires_at=(now + timedelta(seconds=LEASE_SECONDS)).isoformat(),
                      next_run=(now + timedelta(seconds=LEASE_SECONDS)).isoformat())
    return document


def _fingerprint(row):
    fields = {key: value for key, value in row.items()
              if key not in COLLECTOR_FIELDS and key not in {"content_hash", "superseded_at"}}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _merge(document, snapshot, now):
    """Retain every version and allow only a first supersession timestamp update."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("metadata"), dict):
        raise ValueError("Invalid disclosure snapshot")
    if snapshot.get("unchanged"):
        if not document.get("source"):
            raise ValueError("Cannot reuse an absent disclosure snapshot")
        document["source"] = copy.deepcopy(snapshot["metadata"])
        count = len(document["records"]) if "records" in document else document.get("row_count", 0)
        return {"inserted": 0, "duplicates": count, "superseded": 0, "unchanged": True}
    rows = snapshot.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Disclosure source returned no usable rows")
    if len(rows) > MAX_RECORDS:
        raise SnapshotCapacity()
    existing = {row["disclosure_id"]: row for row in document.get("records", [])}
    seen = set()
    counts = {"inserted": 0, "duplicates": 0, "superseded": 0, "unchanged": False}
    timestamp = now.isoformat()
    for incoming in rows:
        if not isinstance(incoming, dict) or COLLECTOR_FIELDS.intersection(incoming):
            raise ValueError("Invalid source disclosure fields")
        key, event, version = incoming.get("disclosure_id"), incoming.get("event_id"), incoming.get("version")
        if (not isinstance(key, str) or not key or len(key) > 300 or not isinstance(event, str)
                or not event or type(version) is not int or version < 1 or key in seen):
            raise ValueError("Invalid or duplicate disclosure identity")
        seen.add(key)
        fingerprint = _fingerprint(incoming)
        previous = existing.get(key)
        if previous is None:
            row = copy.deepcopy(incoming)
            row.update(first_seen_at=timestamp, observed_at=timestamp, last_seen_at=timestamp,
                       content_hash=fingerprint)
            existing[key] = row
            counts["inserted"] += 1
            continue
        if _fingerprint(previous) != fingerprint:
            raise SnapshotConflict()
        prior_superseded, superseded = previous.get("superseded_at"), incoming.get("superseded_at")
        if prior_superseded != superseded:
            if prior_superseded is not None or _time(superseded) is None:
                raise SnapshotConflict()
            previous["superseded_at"] = superseded
            previous["supersession_observed_at"] = timestamp
            counts["superseded"] += 1
        previous["last_seen_at"] = timestamp
        counts["duplicates"] += 1
    refreshed_years = set(snapshot["metadata"].get("years", []))
    for key, row in existing.items():
        available = _time(row.get("provider_available_at"))
        if available is not None and available.year in refreshed_years and key not in seen:
            # An upstream removal or newly excluded ticker must not leave a stale
            # trade looking current under the new source revision. A year outside
            # this snapshot's fetched scope remains retained historical evidence.
            raise SnapshotWithdrawal()
    if len(existing) > MAX_RECORDS:
        raise SnapshotCapacity()
    document["records"] = sorted(existing.values(), key=lambda row: (row.get("available_date", ""), row["event_id"], row["version"]))
    document["source"] = copy.deepcopy(snapshot["metadata"])
    document["revision"] = document.get("revision", 0) + 1
    return counts


def _finish(document, token, now, snapshot=None, error=None):
    if not document or document.get("collection", {}).get("lease_token") != token:
        return document or _empty()
    collection = document["collection"]
    # An expired worker may not publish after another process can claim its lease.
    expiry = _time(collection.get("lease_expires_at"))
    if expiry is None or expiry <= now:
        return document
    if error is None:
        counts = _merge(document, snapshot, now)
        collection.update(state="completed", last_success=now.isoformat(), last_error=None,
                          consecutive_failures=0, counts=counts,
                          next_run=(now + timedelta(seconds=interval_seconds())).isoformat())
    else:
        failures = min(collection.get("consecutive_failures", 0) + 1, 20)
        retry_seconds = min(3600, 300 * 2 ** (failures - 1))
        collection.update(state="failed", last_error=error, consecutive_failures=failures,
                          next_run=(now + timedelta(seconds=retry_seconds)).isoformat())
    collection.pop("lease_token", None)
    collection.pop("lease_expires_at", None)
    return document


def _safe_error(exc):
    if isinstance(exc, SnapshotWithdrawal):
        return "The source removed or excluded a previously collected disclosure. Prior data is retained; the source requires review."
    if isinstance(exc, SnapshotConflict):
        return "The source changed an existing disclosure version. Prior data is retained; the source requires review."
    if isinstance(exc, SnapshotCapacity):
        return "Disclosure history reached the 50,000-version capacity. Prior data is retained; increase storage capacity before retrying."
    return "The disclosure source could not be collected or validated. Prior data is retained; collection will retry automatically."


def collect(*, force=False):
    """Attempt one refresh; forced refresh still respects configuration and leases."""
    if not enabled():
        return status()
    token = str(uuid4())
    document = storage.mutate_feed_metadata(DOCUMENT_ID, lambda previous: _claim(previous, token, utcnow(), force))
    if document.get("collection", {}).get("lease_token") != token:
        return status(document)
    try:
        from backend.trading import disclosure_source
        snapshot = disclosure_source.fetch_snapshot(previous=copy.deepcopy(document.get("source")), now=utcnow())
        mutate = storage.mutate_feed_metadata if snapshot.get("unchanged") else storage.mutate
        document = mutate(DOCUMENT_ID, lambda previous: _finish(previous, token, utcnow(), snapshot=snapshot))
    except Exception as exc:
        logger.warning("Disclosure collection failed (%s)", type(exc).__name__)
        document = storage.mutate_feed_metadata(DOCUMENT_ID, lambda previous: _finish(previous, token, utcnow(), error=_safe_error(exc)))
    return status(document)


async def run_scheduler(stop):
    """Poll compact status so manual refreshes can move the durable retry time."""
    while not stop.is_set():
        try:
            current = await asyncio.to_thread(status)
            due = _time(current.get("next_run"))
            if current["enabled"] and (due is None or due <= utcnow()):
                await asyncio.to_thread(collect)
        except Exception as exc:
            logger.warning("Disclosure scheduler check failed (%s)", type(exc).__name__)
        if stop.is_set():
            break
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
        except asyncio.TimeoutError:
            pass


async def stop_scheduler(task, stop):
    stop.set()
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=5)
    except asyncio.TimeoutError:
        # The bounded source request can finish during process shutdown. If the
        # host terminates it, the persisted lease expires without losing history.
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
