"""SQUAD: cria ledger de uso dos workflows

Revision ID: c4b0e1a92f11
Revises: 3b8d9f6a1c22
Create Date: 2026-03-08 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4b0e1a92f11'
down_revision = '3b8d9f6a1c22'
branch_labels = None
depends_on = None


TABLE_NAME = 'workflow_execution_logs'
INDEXES = {
    'idx_workflow_usage_company': ['company_id'],
    'idx_workflow_usage_action': ['action_key'],
    'idx_workflow_usage_channel': ['channel'],
    'idx_workflow_usage_thread': ['thread_id'],
}


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get('name') == index_name for index in inspector.get_indexes(table_name))


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column.get('name') == column_name for column in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('agent_menu_options'):
        if not _column_exists(inspector, 'agent_menu_options', 'usage_count'):
            op.add_column('agent_menu_options', sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'))
        inspector = sa.inspect(bind)
        if not _column_exists(inspector, 'agent_menu_options', 'last_used_at'):
            op.add_column('agent_menu_options', sa.Column('last_used_at', sa.DateTime(), nullable=True))

    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('session_id', sa.Integer(), nullable=True),
            sa.Column('workflow_option_id', sa.Integer(), nullable=True),
            sa.Column('workflow_code', sa.String(length=40), nullable=False),
            sa.Column('action_key', sa.String(length=120), nullable=True),
            sa.Column('channel', sa.String(length=50), nullable=False, server_default='web'),
            sa.Column('thread_id', sa.String(length=120), nullable=True),
            sa.Column('route_source', sa.String(length=40), nullable=True),
            sa.Column('intercept_stage', sa.String(length=60), nullable=True),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='selected'),
            sa.Column('confidence_route', sa.String(length=30), nullable=True),
            sa.Column('request_text', sa.Text(), nullable=True),
            sa.Column('response_text', sa.Text(), nullable=True),
            sa.Column('metadata_json', sa.JSON(), nullable=True),
            sa.Column('interaction_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
            sa.ForeignKeyConstraint(['session_id'], ['agent_menu_sessions.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['workflow_option_id'], ['agent_menu_options.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)

    for index_name, columns in INDEXES.items():
        if inspector.has_table(TABLE_NAME) and not _index_exists(inspector, TABLE_NAME, index_name):
            op.create_index(index_name, TABLE_NAME, columns, unique=False)
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
