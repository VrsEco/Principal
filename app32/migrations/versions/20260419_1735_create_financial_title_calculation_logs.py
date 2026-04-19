"""create financial title calculation logs

Revision ID: 20260419_1735
Revises: 20260419_1600
Create Date: 2026-04-19 17:35:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260419_1735"
down_revision = "20260419_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_title_calculation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("financial_schedule_id", sa.Integer(), sa.ForeignKey("financial_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("financial_entry_id", sa.Integer(), sa.ForeignKey("financial_entries.id", ondelete="SET NULL"), nullable=True),
        sa.Column("financial_settlement_id", sa.Integer(), sa.ForeignKey("financial_settlements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False, server_default="settlement_posted"),
        sa.Column("calculation_date", sa.Date(), nullable=False),
        sa.Column("template_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("correction_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("updated_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("settled_principal_before", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("settled_principal_current", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("settled_principal_after", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("open_principal_after", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_financial_title_calc_logs_company", "financial_title_calculation_logs", ["company_id"])
    op.create_index("ix_financial_title_calc_logs_schedule", "financial_title_calculation_logs", ["financial_schedule_id"])
    op.create_index("ix_financial_title_calc_logs_entry", "financial_title_calculation_logs", ["financial_entry_id"])
    op.create_index("ix_financial_title_calc_logs_settlement", "financial_title_calculation_logs", ["financial_settlement_id"])
    op.create_index("ix_financial_title_calc_logs_date", "financial_title_calculation_logs", ["calculation_date"])
    op.create_index("ix_financial_title_calc_logs_event", "financial_title_calculation_logs", ["event_type"])


def downgrade():
    op.drop_index("ix_financial_title_calc_logs_event", table_name="financial_title_calculation_logs")
    op.drop_index("ix_financial_title_calc_logs_date", table_name="financial_title_calculation_logs")
    op.drop_index("ix_financial_title_calc_logs_settlement", table_name="financial_title_calculation_logs")
    op.drop_index("ix_financial_title_calc_logs_entry", table_name="financial_title_calculation_logs")
    op.drop_index("ix_financial_title_calc_logs_schedule", table_name="financial_title_calculation_logs")
    op.drop_index("ix_financial_title_calc_logs_company", table_name="financial_title_calculation_logs")
    op.drop_table("financial_title_calculation_logs")
