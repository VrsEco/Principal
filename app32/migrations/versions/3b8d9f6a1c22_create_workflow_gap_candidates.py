"""SQUAD: cria tabela de radar de gaps de workflows

Revision ID: 3b8d9f6a1c22
Revises: d29186829dc9
Create Date: 2026-03-08 11:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b8d9f6a1c22'
down_revision = 'd29186829dc9'
branch_labels = None
depends_on = None


TABLE_NAME = 'workflow_gap_candidates'
INDEXES = {
    'idx_workflow_gap_company': ['company_id'],
    'idx_workflow_gap_thread': ['thread_id'],
    'idx_workflow_gap_user': ['user_id'],
}


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get('name') == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('channel', sa.String(length=50), nullable=False, server_default='web'),
            sa.Column('thread_id', sa.String(length=120), nullable=True),
            sa.Column('source', sa.String(length=50), nullable=False, server_default='ai_fallback'),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='inbox'),
            sa.Column('resolution_type', sa.String(length=30), nullable=False, server_default='resolved_by_ai'),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('user_request_text', sa.Text(), nullable=False),
            sa.Column('normalized_intent', sa.String(length=255), nullable=True),
            sa.Column('suggested_flow_name', sa.String(length=255), nullable=True),
            sa.Column('business_outcome', sa.Text(), nullable=True),
            sa.Column('matched_workflow_codes', sa.JSON(), nullable=True),
            sa.Column('telemetry', sa.JSON(), nullable=True),
            sa.Column('app_project_id', sa.Integer(), nullable=True),
            sa.Column('app_task_id', sa.Integer(), nullable=True),
            sa.Column('app_task_code', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['app_project_id'], ['projects.id']),
            sa.ForeignKeyConstraint(['app_task_id'], ['project_tasks.id']),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(bind)

    for index_name, columns in INDEXES.items():
        if not _index_exists(inspector, TABLE_NAME, index_name):
            op.create_index(index_name, TABLE_NAME, columns, unique=False)
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
