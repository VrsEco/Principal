"""Add a tenant-scoped index for paginated project listings.

Revision ID: 20260913_1200
Revises: 20260913_1100
Create Date: 2026-09-13 14:00:00.000000
"""

from alembic import op


revision = "20260913_1200"
down_revision = "20260913_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_projects_company_id", "projects", ["company_id", "id"])


def downgrade():
    op.drop_index("ix_projects_company_id", table_name="projects")
