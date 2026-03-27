"""merge financial heads after launches and budget execution reorg

Revision ID: 20260327_1200
Revises: 20260327_1000, 20260327_1130
Create Date: 2026-03-27 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260327_1200"
down_revision = ("20260327_1000", "20260327_1130")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
