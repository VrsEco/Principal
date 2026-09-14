"""Add tenant-scoped index for paginated financial automation records.

Revision ID: 20260913_1400
Revises: 20260913_1300
Create Date: 2026-09-13 23:00:00.000000
"""

from alembic import op


revision = "20260913_1400"
down_revision = "20260913_1300"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_financial_automation_records_company_created_id",
        "financial_automation_records",
        ["company_id", "created_at", "id"],
    )


def downgrade():
    op.drop_index(
        "ix_financial_automation_records_company_created_id",
        table_name="financial_automation_records",
    )
