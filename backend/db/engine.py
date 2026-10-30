"""Database configuration, without implicit schema creation or file fallback."""

import os
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool


def create_database_engine(database_url, *, allow_sqlite=False):
    try:
        url = make_url(database_url)
    except Exception:
        raise ValueError("DATABASE_URL is not a valid database connection URL") from None
    if url.drivername in {"postgres", "postgresql", "postgresql+psycopg"}:
        url = url.set(drivername="postgresql+psycopg")
        host = url.host or url.query.get("host", "")
        if isinstance(host, str) and host.endswith((".supabase.co", ".supabase.com")):
            if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
                url = url.update_query_dict({"sslmode": "require"})
        return create_engine(
            url, pool_pre_ping=True, pool_timeout=10, hide_parameters=True,
            connect_args={
                "prepare_threshold": None,
                "connect_timeout": 8,
                "keepalives": 1, "keepalives_idle": 10,
                "keepalives_interval": 5, "keepalives_count": 3,
                "tcp_user_timeout": 15000,
                "options": "-c statement_timeout=30000",
            },
        )
    if allow_sqlite and url.drivername == "sqlite":
        options = {"poolclass": StaticPool} if url.database in {None, "", ":memory:"} else {}
        engine = create_engine(url, hide_parameters=True, connect_args={"check_same_thread": False}, **options)

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        return engine
    raise ValueError("DATABASE_URL must use PostgreSQL; SQLite is reserved for offline tests")


@lru_cache(maxsize=4)
def _configured_repository(database_url):
    from backend.db.repository import ResearchRepository
    return ResearchRepository(create_database_engine(database_url))


def get_repository():
    """Return None only when DATABASE_URL is absent; configured failures propagate."""
    database_url = os.getenv("DATABASE_URL")
    if database_url is None or database_url == "":
        return None
    return _configured_repository(database_url)
