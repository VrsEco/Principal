"""create financial title adjustment allocations

Revision ID: 20260420_1100
Revises: 20260420_1000
Create Date: 2026-04-20 11:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_1100"
down_revision = "20260420_1000"
branch_labels = None
depends_on = None


TABLE_NAME = "financial_title_adjustment_allocations"
INDEX_DEFINITIONS = (
    ("ix_fin_title_adj_alloc_company_adjustment", ["company_id", "financial_title_adjustment_id"]),
    ("ix_fin_title_adj_alloc_company_chart_cost", ["company_id", "chart_account_id", "cost_center_id"]),
)


def _table_exists(inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column(
                "financial_title_adjustment_id",
                sa.Integer(),
                sa.ForeignKey("financial_title_adjustments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column(
                "budget_document_id",
                sa.Integer(),
                sa.ForeignKey("financial_budget_documents.id"),
                nullable=True,
            ),
            sa.Column(
                "activity_id",
                sa.Integer(),
                sa.ForeignKey("process_routines.id"),
                nullable=True,
            ),
            sa.Column(
                "process_instance_id",
                sa.Integer(),
                sa.ForeignKey("process_instances.id"),
                nullable=True,
            ),
            sa.Column(
                "routine_id",
                sa.Integer(),
                sa.ForeignKey("routines.id"),
                nullable=True,
            ),
            sa.Column("percentage", sa.Numeric(9, 4), nullable=True),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column(
                "metadata_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
            sa.CheckConstraint(
                "(percentage IS NULL) OR (percentage >= 0 AND percentage <= 100)",
                name="ck_financial_title_adjustment_allocations_percentage_range",
            ),
            sa.CheckConstraint(
                "amount >= 0",
                name="ck_financial_title_adjustment_allocations_amount_nonneg",
            ),
        )
        inspector = sa.inspect(bind)

    for index_name, columns in INDEX_DEFINITIONS:
        if not _index_exists(inspector, TABLE_NAME, index_name):
            op.create_index(index_name, TABLE_NAME, columns, unique=False)
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, TABLE_NAME):
        return

    for index_name, _ in reversed(INDEX_DEFINITIONS):
        if _index_exists(inspector, TABLE_NAME, index_name):
            op.drop_index(index_name, table_name=TABLE_NAME)
            inspector = sa.inspect(bind)

    op.drop_table(TABLE_NAME)
