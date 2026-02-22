"""fix employee unique constraint to allow multi-company links

Revision ID: 20251201_1900
Revises: 20251201_1700
Create Date: 2025-12-01 19:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251201_1900"
down_revision = "20251201_1700"
branch_labels = None
depends_on = None


def upgrade():
    # Remove legacy index that forced a single employee per user globally
    op.execute("DROP INDEX IF EXISTS idx_employees_user_unique;")

    # Drop previous composite indexes to ensure a clean state
    op.execute("DROP INDEX IF EXISTS idx_employees_user_company_unique;")
    op.execute("DROP INDEX IF EXISTS idx_employees_user_id;")

    # Ensure one employee per company for each user, allowing multi-company assignments
    op.create_index(
        "idx_employees_user_company_unique",
        "employees",
        ["user_id", "company_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    # Add a partial index on user_id for lookups without re-introducing the uniqueness bug
    op.create_index(
        "idx_employees_user_id",
        "employees",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_employees_user_company_unique;")
    op.execute("DROP INDEX IF EXISTS idx_employees_user_id;")

    # Restore the old behavior (single employee per user) if needed
    op.create_index(
        "idx_employees_user_unique",
        "employees",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
