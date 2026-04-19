"""create financial settlement components

Revision ID: 20260420_0900
Revises: 20260419_1735
Create Date: 2026-04-20 09:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_0900"
down_revision = "20260419_1735"
branch_labels = None
depends_on = None


TABLE_NAME = "financial_settlement_components"
INDEX_DEFINITIONS = (
    ("ix_fin_settlement_components_company_settlement", ["company_id", "financial_settlement_id"]),
    ("ix_fin_settlement_components_company_schedule", ["company_id", "financial_schedule_id"]),
    ("ix_fin_settlement_components_company_type_competence", ["company_id", "component_type", "competence_date"]),
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
            sa.Column(
                "financial_settlement_id",
                sa.Integer(),
                sa.ForeignKey("financial_settlements.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "financial_schedule_id",
                sa.Integer(),
                sa.ForeignKey("financial_schedules.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("component_type", sa.String(length=30), nullable=False),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("competence_date", sa.Date(), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("source", sa.String(length=20), nullable=False, server_default="system"),
            sa.Column("origin_adjustment_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
            sa.CheckConstraint(
                "component_type IN ('principal', 'monetary_correction', 'interest', 'fine', 'discount', 'manual_adjustment')",
                name="ck_financial_settlement_components_type",
            ),
            sa.CheckConstraint(
                "amount >= 0",
                name="ck_financial_settlement_components_amount_nonneg",
            ),
        )
        inspector = sa.inspect(bind)

    for index_name, columns in INDEX_DEFINITIONS:
        if not _index_exists(inspector, index_name):
            op.create_index(index_name, TABLE_NAME, columns, unique=False)
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
