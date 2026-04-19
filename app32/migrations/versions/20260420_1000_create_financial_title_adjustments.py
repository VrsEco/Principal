"""create financial title adjustments

Revision ID: 20260420_1000
Revises: 20260420_0900
Create Date: 2026-04-20 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_1000"
down_revision = "20260420_0900"
branch_labels = None
depends_on = None


TABLE_NAME = "financial_title_adjustments"
SETTLEMENT_COMPONENTS_TABLE = "financial_settlement_components"
SETTLEMENT_COMPONENTS_FK_NAME = "fk_fin_settlement_components_origin_adjustment_id"
INDEX_DEFINITIONS = (
    ("ix_fin_title_adjustments_company_schedule", ["company_id", "financial_schedule_id"]),
    ("ix_fin_title_adjustments_company_type_status", ["company_id", "adjustment_type", "status"]),
    ("ix_fin_title_adjustments_company_competence", ["company_id", "competence_date"]),
)
SETTLEMENT_COMPONENTS_INDEX = (
    "ix_fin_settlement_components_origin_adjustment_id",
    ["origin_adjustment_id"],
)


def _table_exists(inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _foreign_key_exists(inspector, table_name: str, constraint_name: str) -> bool:
    return any(fk.get("name") == constraint_name for fk in inspector.get_foreign_keys(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column(
                "financial_schedule_id",
                sa.Integer(),
                sa.ForeignKey("financial_schedules.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("adjustment_type", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("calculation_date", sa.Date(), nullable=False),
            sa.Column("competence_date", sa.Date(), nullable=False),
            sa.Column("due_date_reference", sa.Date(), nullable=True),
            sa.Column("base_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("generated_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("settled_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("open_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column(
                "rule_snapshot_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "metadata_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "adjustment_type IN ('monetary_correction', 'interest', 'fine', 'discount', 'writeoff')",
                name="ck_financial_title_adjustments_type",
            ),
            sa.CheckConstraint(
                "status IN ('open', 'partial', 'settled', 'cancelled')",
                name="ck_financial_title_adjustments_status",
            ),
            sa.CheckConstraint(
                "base_amount >= 0 AND generated_amount >= 0 AND settled_amount >= 0 AND open_amount >= 0",
                name="ck_financial_title_adjustments_amounts_nonneg",
            ),
        )
        inspector = sa.inspect(bind)

    for index_name, columns in INDEX_DEFINITIONS:
        if not _index_exists(inspector, TABLE_NAME, index_name):
            op.create_index(index_name, TABLE_NAME, columns, unique=False)
            inspector = sa.inspect(bind)

    if _table_exists(inspector, SETTLEMENT_COMPONENTS_TABLE):
        index_name, columns = SETTLEMENT_COMPONENTS_INDEX
        if not _index_exists(inspector, SETTLEMENT_COMPONENTS_TABLE, index_name):
            op.create_index(index_name, SETTLEMENT_COMPONENTS_TABLE, columns, unique=False)
            inspector = sa.inspect(bind)

        if not _foreign_key_exists(inspector, SETTLEMENT_COMPONENTS_TABLE, SETTLEMENT_COMPONENTS_FK_NAME):
            op.create_foreign_key(
                SETTLEMENT_COMPONENTS_FK_NAME,
                SETTLEMENT_COMPONENTS_TABLE,
                TABLE_NAME,
                ["origin_adjustment_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, SETTLEMENT_COMPONENTS_TABLE):
        if _foreign_key_exists(inspector, SETTLEMENT_COMPONENTS_TABLE, SETTLEMENT_COMPONENTS_FK_NAME):
            op.drop_constraint(SETTLEMENT_COMPONENTS_FK_NAME, SETTLEMENT_COMPONENTS_TABLE, type_="foreignkey")
            inspector = sa.inspect(bind)

        index_name, _ = SETTLEMENT_COMPONENTS_INDEX
        if _index_exists(inspector, SETTLEMENT_COMPONENTS_TABLE, index_name):
            op.drop_index(index_name, table_name=SETTLEMENT_COMPONENTS_TABLE)
            inspector = sa.inspect(bind)

    if not _table_exists(inspector, TABLE_NAME):
        return

    for index_name, _ in reversed(INDEX_DEFINITIONS):
        if _index_exists(inspector, TABLE_NAME, index_name):
            op.drop_index(index_name, table_name=TABLE_NAME)
            inspector = sa.inspect(bind)

    op.drop_table(TABLE_NAME)
