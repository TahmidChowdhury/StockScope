"""Additive workspace schema with its own version, compatible with deployed research API."""
import os
from alembic import context
from dotenv import load_dotenv
from backend.db.engine import create_database_engine

load_dotenv()
config = context.config


def migrate(connection):
    context.configure(connection=connection, version_table='workspace_schema_version')
    with context.begin_transaction():
        context.run_migrations()


supplied = config.attributes.get('connection')
if supplied is not None:
    migrate(supplied)
elif context.is_offline_mode():
    raise RuntimeError('Workspace migrations require an online connection')
else:
    engine = create_database_engine(os.environ['DATABASE_URL'])
    with engine.connect() as connection:
        migrate(connection)
    engine.dispose()
