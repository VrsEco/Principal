"""allow negative discount allocations

Revision ID: 20260329_1400
Revises: 20260328_1000
Create Date: 2026-03-29 14:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260329_1400"
down_revision = "20260328_1000"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_financial_entry_allocations_nonneg", "financial_entry_allocations", type_="check")
    op.create_check_constraint(
        "ck_financial_entry_allocations_nonneg",
        "financial_entry_allocations",
        "(percentage IS NULL OR percentage >= 0)",
    )


def downgrade():
    op.drop_constraint("ck_financial_entry_allocations_nonneg", "financial_entry_allocations", type_="check")
    op.create_check_constraint(
        "ck_financial_entry_allocations_nonneg",
        "financial_entry_allocations",
        "(percentage IS NULL OR percentage >= 0) AND (allocated_amount IS NULL OR allocated_amount >= 0)",
    )
