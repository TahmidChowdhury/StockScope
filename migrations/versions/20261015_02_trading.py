"""Shared paper portfolios, Congress evidence, and saved backtest runs."""
from alembic import op
import sqlalchemy as sa

revision = "20261015_02"
down_revision = "20261014_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("trading_documents", sa.Column("id", sa.String(80), primary_key=True),
                    sa.Column("kind", sa.String(20), nullable=False),
                    sa.Column("payload", sa.JSON(), nullable=False),
                    sa.Column("summary", sa.JSON(), nullable=False))
    op.create_index("ix_trading_documents_kind", "trading_documents", ["kind"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE trading_documents ENABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL ON TABLE trading_documents FROM PUBLIC")
        op.execute(sa.text("""DO $$ DECLARE role_name text; BEGIN
            FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('REVOKE ALL ON TABLE trading_documents FROM %I', role_name);
                END IF;
            END LOOP;
        END $$"""))


def downgrade():
    op.drop_index("ix_trading_documents_kind", table_name="trading_documents")
    op.drop_table("trading_documents")
