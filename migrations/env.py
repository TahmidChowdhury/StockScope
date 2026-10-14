"""Explicit migration runner; application startup never runs DDL."""

import os

from alembic import context
from dotenv import load_dotenv

from backend.db.engine import create_database_engine
from backend.db.models import Base

load_dotenv()
config = context.config


def database_url():
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required to run migrations")
    return value


def run_migrations_offline():
    engine = create_database_engine(database_url())
    context.configure(url=engine.url, target_metadata=Base.metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Tests may supply a local SQLite connection, never via production DATABASE_URL.
    supplied = config.attributes.get("connection")
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_database_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
