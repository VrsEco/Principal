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

TABLE_NAME = "financial_title_calculation_logs"
INDEX_DEFINITIONS = (
    ("ix_financial_title_calc_logs_company", ["company_id"]),
    ("ix_financial_title_calc_logs_schedule", ["financial_schedule_id"]),
    ("ix_financial_title_calc_logs_entry", ["financial_entry_id"]),
    ("ix_financial_title_calc_logs_settlement", ["financial_settlement_id"]),
    ("ix_financial_title_calc_logs_date", ["calculation_date"]),
    ("ix_financial_title_calc_logs_event", ["event_type"]),
)


def _table_exists(inspector) -> bool:
    return inspector.has_table(TABLE_NAME)


def _index_exists(inspector, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(TABLE_NAME))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector):
        op.create_table(
            TABLE_NAME,
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
        inspector = sa.inspect(bind)

    for index_name, columns in INDEX_DEFINITIONS:
        if not _index_exists(inspector, index_name):
            op.create_index(index_name, TABLE_NAME, columns)
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector):
        return

    for index_name, _ in reversed(INDEX_DEFINITIONS):
        if _index_exists(inspector, index_name):
            op.drop_index(index_name, table_name=TABLE_NAME)
            inspector = sa.inspect(bind)

    op.drop_table(TABLE_NAME)
