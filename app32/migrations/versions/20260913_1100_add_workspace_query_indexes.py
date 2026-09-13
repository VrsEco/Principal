"""Add indexes for tenant-scoped portfolio and meeting workspaces.

Revision ID: 20260913_1100
Revises: 20260913_1000
Create Date: 2026-09-13 13:00:00.000000
"""

from alembic import op


revision = "20260913_1100"
down_revision = "20260913_1000"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_projects_company_portfolio_id", "projects", ["company_id", "portfolio_id"]),
    ("ix_meetings_company_created_at", "meetings", ["company_id", "created_at"]),
)


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
