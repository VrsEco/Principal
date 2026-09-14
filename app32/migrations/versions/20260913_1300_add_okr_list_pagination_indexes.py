"""Add tenant-scoped indexes for paginated OKR listings.

Revision ID: 20260913_1300
Revises: 20260913_1200
Create Date: 2026-09-13 22:30:00.000000
"""

from alembic import op


revision = "20260913_1300"
down_revision = "20260913_1200"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_okrs_global_company_deadline_id", "okrs_global", ["company_id", "deadline", "id"]),
    ("ix_okrs_area_company_deadline_id", "okrs_area", ["company_id", "deadline", "id"]),
)


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
