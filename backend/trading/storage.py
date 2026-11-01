"""Atomic shared documents, using the configured authoritative storage only."""
from __future__ import annotations

import copy
import json
import os
import re
from contextlib import contextmanager
from threading import RLock

from sqlalchemy import JSON, cast, literal, select, update
from sqlalchemy.orm import Session

from backend.core.atomic_file import atomic_text_writer
from backend.db.models import TradingDocument
from backend.services import research

_lock = RLock()


def _key(key):
    if not re.fullmatch(r"(?:congress|congress-feed|portfolio-[a-f0-9-]{36}|run-[a-f0-9-]{36})", key):
        raise ValueError("Invalid trading document id")
    return key


def _summary(document):
    keys = ("id", "name", "kind", "created_at", "initial_cash", "benchmark", "strategy", "start", "end", "member", "revision")
    result = {k: document[k] for k in keys if k in document}
    if document.get("result"):
        result["metrics"] = document["result"]["metrics"]
        result["as_of"] = document["result"]["as_of"]
    if document.get("kind") == "congress_feed":
        result["source"] = document.get("source", {})
        result["row_count"] = len(document["records"]) if "records" in document else document.get("row_count", 0)
        result["collection"] = {key: value for key, value in document.get("collection", {}).items()
                                if key != "lease_token"}
    return result


@contextmanager
def _file_lock():
    # Existing deployment supports one worker; flock also prevents lost local-process writes.
    import fcntl
    directory = research.data_directory() / "trading"
    directory.mkdir(parents=True, exist_ok=True)
    with _lock, (directory / ".lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield directory
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read(key):
    _key(key)
    repo = research.repository()
    if repo is not None:
        with Session(repo.engine) as session:
            row = session.get(TradingDocument, key)
            return copy.deepcopy(row.payload) if row else None
    with _file_lock() as directory:
        path = directory / f"{key}.json"
        return json.loads(path.read_text()) if path.exists() else None


def read_summary(key):
    """Read compact metadata without downloading an entire disclosure history."""
    _key(key)
    repo = research.repository()
    if repo is not None:
        with Session(repo.engine) as session:
            return copy.deepcopy(session.scalar(select(TradingDocument.summary).where(TradingDocument.id == key)))
    document = read(key)
    return _summary(document) if document else None


def mutate_feed_metadata(key, callback):
    """Update collection state without transferring the PostgreSQL history payload.

The callback receives compact metadata plus the private lease. JSONB concatenation
changes only these top-level metadata fields server-side; records stay untouched.
SQLite and file mode use the same atomic mutation with an in-process projection.
"""
    _key(key)
    fields = ("id", "kind", "revision", "source", "collection")

    def project(document):
        if not document:
            return None
        result = _summary(document)
        result["collection"] = copy.deepcopy(document.get("collection", {}))
        return result

    def validate(previous, document):
        if document.get("kind") != "congress_feed":
            raise ValueError("Metadata updates require a disclosure feed document")
        before = (previous or {}).get("row_count", 0)
        after = len(document["records"]) if "records" in document else document.get("row_count", 0)
        if before != after:
            raise ValueError("A metadata update cannot change disclosure history")
        json.dumps(document, allow_nan=False)

    repo = research.repository()
    if repo is None or repo.engine.dialect.name != "postgresql":
        def apply(previous):
            metadata = project(previous)
            result = callback(copy.deepcopy(metadata))
            validate(metadata, result)
            document = previous or {"records": []}
            document.update({field: copy.deepcopy(result[field]) for field in fields if field in result})
            return document
        return project(mutate(key, apply))

    from sqlalchemy.dialects.postgresql import JSONB, insert
    with Session(repo.engine) as session, session.begin():
        session.execute(insert(TradingDocument).values(id=key, kind="congress_feed", payload={"records": []}, summary={})
                        .on_conflict_do_nothing(index_elements=["id"]))
        stored, collection = session.execute(select(TradingDocument.summary, TradingDocument.payload["collection"])
                                             .where(TradingDocument.id == key).with_for_update()).one()
        previous = copy.deepcopy(stored) if stored else None
        if previous is not None:
            previous["collection"] = copy.deepcopy(collection or {})
        document = callback(copy.deepcopy(previous))
        validate(previous, document)
        metadata = {field: copy.deepcopy(document[field]) for field in fields if field in document}
        payload = cast(cast(TradingDocument.payload, JSONB).op("||")(literal(metadata, type_=JSONB)), JSON)
        session.execute(update(TradingDocument).where(TradingDocument.id == key)
                        .values(kind="congress_feed", payload=payload, summary=_summary(document)))
        return project(document)


def listing(kind):
    repo = research.repository()
    if repo is not None:
        with Session(repo.engine) as session:
            rows = session.scalars(select(TradingDocument.summary).where(TradingDocument.kind == kind)).all()
            return sorted(rows, key=lambda row: row["created_at"], reverse=True)
    with _file_lock() as directory:
        rows = [_summary(json.loads(path.read_text())) for path in directory.glob(f"{kind}-*.json")]
        return sorted(rows, key=lambda row: row["created_at"], reverse=True)


def mutate(key, callback):
    """Serialize read/modify/write; callback exceptions roll back the complete operation."""
    _key(key)
    repo = research.repository()
    if repo is not None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        insert = pg_insert if repo.engine.dialect.name == "postgresql" else sqlite_insert
        with Session(repo.engine) as session, session.begin():
            session.execute(insert(TradingDocument).values(id=key, kind=key.split("-")[0], payload={}, summary={}).on_conflict_do_nothing(index_elements=["id"]))
            row = session.scalar(select(TradingDocument).where(TradingDocument.id == key).with_for_update())
            document = callback(copy.deepcopy(row.payload) or None)
            # Reject non-JSON/nonfinite payloads before committing either storage mode.
            json.dumps(document, allow_nan=False)
            row.kind = document.get("kind", row.kind)
            row.payload, row.summary = document, _summary(document)
            return document
    with _file_lock() as directory:
        path = directory / f"{key}.json"
        previous = json.loads(path.read_text()) if path.exists() else None
        document = callback(previous)
        encoded = json.dumps(document, allow_nan=False)
        with atomic_text_writer(path) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return document
