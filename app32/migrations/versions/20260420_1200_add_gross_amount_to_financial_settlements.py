"""add gross amount to financial settlements

Revision ID: 20260420_1200
Revises: 20260420_1100
Create Date: 2026-04-20 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260420_1200"
down_revision = "20260420_1100"
branch_labels = None
depends_on = None


TABLE_NAME = "financial_settlements"
COLUMN_NAME = "gross_amount"
CHECK_NAME = "ck_financial_settlements_gross_amount_nonneg"


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def _check_exists(inspector, table_name: str, check_name: str) -> bool:
    return any(check.get("name") == check_name for check in inspector.get_check_constraints(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, TABLE_NAME, COLUMN_NAME):
        op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.Numeric(14, 2), nullable=True, server_default="0"))
        op.execute(
            sa.text(
                """
                UPDATE financial_settlements
                   SET gross_amount = principal_amount + interest_amount + penalty_amount + fee_amount + other_adjustments_amount - discount_amount
                 WHERE gross_amount IS NULL OR gross_amount = 0
                """
            )
        )
        op.alter_column(TABLE_NAME, COLUMN_NAME, existing_type=sa.Numeric(14, 2), nullable=False, server_default=None)
        inspector = sa.inspect(bind)

    if not _check_exists(inspector, TABLE_NAME, CHECK_NAME):
        op.create_check_constraint(CHECK_NAME, TABLE_NAME, "gross_amount >= 0")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _check_exists(inspector, TABLE_NAME, CHECK_NAME):
        op.drop_constraint(CHECK_NAME, TABLE_NAME, type_="check")
        inspector = sa.inspect(bind)

    if _column_exists(inspector, TABLE_NAME, COLUMN_NAME):
        op.drop_column(TABLE_NAME, COLUMN_NAME)
