"""expand financial title calculation logs to ledger

Revision ID: 20260420_1300
Revises: 20260420_1200
Create Date: 2026-04-20 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_1300"
down_revision = "20260420_1200"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_money_column(column_name: str) -> None:
    if not _column_exists("financial_title_calculation_logs", column_name):
        op.add_column(
            "financial_title_calculation_logs",
            sa.Column(column_name, sa.Numeric(14, 2), nullable=False, server_default="0"),
        )
        op.alter_column("financial_title_calculation_logs", column_name, server_default=None)


def upgrade():
    money_columns = (
        "principal_before",
        "adjustments_open_before",
        "total_due_before",
        "principal_settled_now",
        "adjustments_settled_now",
        "discount_now",
        "principal_after",
        "adjustments_open_after",
        "total_due_after",
    )
    for column_name in money_columns:
        _add_money_column(column_name)

    if not _column_exists("financial_title_calculation_logs", "snapshot_json"):
        op.add_column(
            "financial_title_calculation_logs",
            sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )
        op.alter_column("financial_title_calculation_logs", "snapshot_json", server_default=None)

    op.execute(
        """
        UPDATE financial_title_calculation_logs
           SET principal_before = COALESCE(NULLIF(principal_before, 0), open_principal_after + settled_principal_current),
               principal_settled_now = COALESCE(NULLIF(principal_settled_now, 0), settled_principal_current),
               principal_after = COALESCE(NULLIF(principal_after, 0), open_principal_after),
               total_due_after = COALESCE(NULLIF(total_due_after, 0), open_principal_after),
               snapshot_json = CASE
                   WHEN snapshot_json = '{}'::jsonb AND metadata_json ? 'snapshot'
                   THEN metadata_json -> 'snapshot'
                   ELSE snapshot_json
               END
        """
    )


def downgrade():
    for column_name in (
        "snapshot_json",
        "total_due_after",
        "adjustments_open_after",
        "principal_after",
        "discount_now",
        "adjustments_settled_now",
        "principal_settled_now",
        "total_due_before",
        "adjustments_open_before",
        "principal_before",
    ):
        if _column_exists("financial_title_calculation_logs", column_name):
            op.drop_column("financial_title_calculation_logs", column_name)
