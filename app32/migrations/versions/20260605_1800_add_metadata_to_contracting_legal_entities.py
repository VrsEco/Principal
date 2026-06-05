"""add metadata to contracting legal entities

Revision ID: 20260605_1800
Revises: 20260604_1400
Create Date: 2026-06-05 18:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260605_1800"
down_revision = "20260604_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "contracting_legal_entities",
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade():
    op.drop_column("contracting_legal_entities", "metadata_json")
