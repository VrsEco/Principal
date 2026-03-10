"""add_occurrences_collaborators_ids

Revision ID: 20260310_1945
Revises: c4b0e1a92f11
Create Date: 2026-03-10 19:45:00.000000

Descrição:
    Adiciona a coluna nativa collaborators_ids em occurrences para suportar
    ocorrências multi-colaborador de forma compatível com PostgreSQL.
"""

from alembic import op
import sqlalchemy as sa


revision = '20260310_1945'
down_revision = 'c4b0e1a92f11'
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column.get('name') == column_name for column in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('occurrences') and not _column_exists(inspector, 'occurrences', 'collaborators_ids'):
        op.add_column('occurrences', sa.Column('collaborators_ids', sa.JSON(), nullable=True))
        op.execute("UPDATE occurrences SET collaborators_ids = '[]'::json WHERE collaborators_ids IS NULL")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('occurrences') and _column_exists(inspector, 'occurrences', 'collaborators_ids'):
        op.drop_column('occurrences', 'collaborators_ids')
