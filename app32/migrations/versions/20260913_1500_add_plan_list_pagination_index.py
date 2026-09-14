"""Add tenant-scoped index for paginated plan listings.

Revision ID: 20260913_1500
Revises: 20260913_1400
Create Date: 2026-09-13 23:30:00.000000
"""

from alembic import op


revision = "20260913_1500"
down_revision = "20260913_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_plans_company_created_id", "plans", ["company_id", "created_at", "id"])


def downgrade():
    op.drop_index("ix_plans_company_created_id", table_name="plans")
