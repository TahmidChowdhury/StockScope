"""Atomic shared documents, using the configured authoritative storage only."""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from contextlib import contextmanager
from threading import RLock

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import TradingDocument
from backend.services import research

_lock = RLock()


def _key(key):
    if not re.fullmatch(r"(?:congress|portfolio-[a-f0-9-]{36}|run-[a-f0-9-]{36})", key):
        raise ValueError("Invalid trading document id")
    return key


def _summary(document):
    keys = ("id", "name", "kind", "created_at", "initial_cash", "benchmark", "strategy", "start", "end", "member", "revision")
    result = {k: document[k] for k in keys if k in document}
    if document.get("result"):
        result["metrics"] = document["result"]["metrics"]
        result["as_of"] = document["result"]["as_of"]
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
            row.payload, row.summary = document, _summary(document)
            return document
    with _file_lock() as directory:
        path = directory / f"{key}.json"
        previous = json.loads(path.read_text()) if path.exists() else None
        document = callback(previous)
        encoded = json.dumps(document, allow_nan=False)
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as handle:
            temporary = handle.name
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return document
