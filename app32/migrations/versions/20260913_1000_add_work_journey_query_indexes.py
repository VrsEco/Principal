"""Add composite indexes for recurring work journey tenant queries.

Revision ID: 20260913_1000
Revises: 20260912_1700
Create Date: 2026-09-13 12:00:00.000000
"""

from alembic import op


revision = "20260913_1000"
down_revision = "20260912_1700"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_work_journey_blocks_company_employee_active", "work_journey_blocks", ["company_id", "employee_id", "is_active"]),
    ("ix_work_journey_rules_company_employee_active", "work_journey_rules", ["company_id", "employee_id", "is_active"]),
    ("ix_work_journey_items_company_employee_due", "work_journey_items", ["company_id", "employee_id", "due_date"]),
    ("ix_work_journey_items_company_employee_occurrence", "work_journey_items", ["company_id", "employee_id", "occurrence_date"]),
)


def upgrade():
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
