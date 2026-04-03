"""add work journey block mode

Revision ID: 20260403_1900
Revises: 20260403_1800
Create Date: 2026-04-03 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '20260403_1900'
down_revision = '20260403_1800'
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column.get('name') == column_name for column in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, 'work_journey_blocks'):
        return

    if not _has_column(inspector, 'work_journey_blocks', 'block_mode'):
        op.add_column(
            'work_journey_blocks',
            sa.Column('block_mode', sa.String(length=30), nullable=False, server_default='operational'),
        )

    op.execute("UPDATE work_journey_blocks SET block_mode = 'operational' WHERE block_mode IS NULL")
    op.alter_column('work_journey_blocks', 'block_mode', server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, 'work_journey_blocks'):
        return

    if _has_column(inspector, 'work_journey_blocks', 'block_mode'):
        op.drop_column('work_journey_blocks', 'block_mode')
