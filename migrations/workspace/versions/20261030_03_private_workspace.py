"""Invite-only accounts, personal lists, and durable provider budgets."""
from alembic import op
import sqlalchemy as sa

revision = "20261030_03"
down_revision = None
branch_labels = None
depends_on = None
TABLES = ['workspace_users', 'workspace_invites', 'personal_lists', 'personal_list_items', 'resource_state']


def upgrade():
    op.create_table('workspace_users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('session_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('email', name='uq_workspace_users_email'),
        sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name='ck_workspace_users_user_role'))
    op.create_table('workspace_invites',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('workspace_users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('token_hash', name='uq_workspace_invites_token_hash'),
        sa.CheckConstraint("role IN ('admin', 'member', 'viewer')", name='ck_workspace_invites_invite_role'))
    op.create_table('personal_lists',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('workspace_users.id'), nullable=False),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('owner_id', 'name', name='uq_personal_list_name'))
    op.create_index('ix_personal_lists_owner_id', 'personal_lists', ['owner_id'])
    op.create_table('personal_list_items',
        sa.Column('list_id', sa.String(36), sa.ForeignKey('personal_lists.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('symbol', sa.String(10), primary_key=True),
        sa.Column('pinned', sa.Boolean(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('resource_state', sa.Column('key', sa.String(120), primary_key=True), sa.Column('payload', sa.JSON(), nullable=False))
    op.execute(sa.text("INSERT INTO resource_state (key, payload) VALUES ('accounts', '{}')"))
    if op.get_bind().dialect.name == 'postgresql':
        for table in TABLES:
            op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
            op.execute(f'REVOKE ALL ON TABLE {table} FROM PUBLIC')
            for role in ('anon', 'authenticated'):
                op.execute(sa.text(f"""DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    REVOKE ALL ON TABLE {table} FROM {role}; END IF; END $$"""))


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
