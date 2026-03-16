"""feat: add source_id to incentive_indicators

Revision ID: 5db8307519c3
Revises: 77ecdce92559
Create Date: 2026-03-12 22:21:51.796312

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5db8307519c3'
down_revision = '77ecdce92559'
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column.get('name') == column_name for column in columns)


def upgrade():
    if not _has_column('incentive_indicators', 'source_id'):
        with op.batch_alter_table('incentive_indicators', schema=None) as batch_op:
            batch_op.add_column(sa.Column('source_id', sa.Integer(), nullable=True))

def downgrade():
    if _has_column('incentive_indicators', 'source_id'):
        with op.batch_alter_table('incentive_indicators', schema=None) as batch_op:
            batch_op.drop_column('source_id')
