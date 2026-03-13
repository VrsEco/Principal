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

def upgrade():
    # Only add source_id to incentive_indicators
    with op.batch_alter_table('incentive_indicators', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_id', sa.Integer(), nullable=True))

def downgrade():
    with op.batch_alter_table('incentive_indicators', schema=None) as batch_op:
        batch_op.drop_column('source_id')
