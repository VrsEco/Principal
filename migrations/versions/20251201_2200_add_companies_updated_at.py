"""add missing updated_at column to companies

Revision ID: 20251201_2200
Revises: 20251201_2100
Create Date: 2025-12-01 22:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251201_2200"
down_revision = "20251201_2100"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    """Check if the given table already has the column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade():
    if not _has_column("companies", "updated_at"):
        with op.batch_alter_table("companies") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("now()"),
                )
            )


def downgrade():
    if _has_column("companies", "updated_at"):
        with op.batch_alter_table("companies") as batch_op:
            batch_op.drop_column("updated_at")













