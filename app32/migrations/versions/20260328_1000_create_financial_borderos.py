"""create financial borderos

Revision ID: 20260328_1000
Revises: 20260328_0900
Create Date: 2026-03-28 10:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_1000"
down_revision = "20260328_0900"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    if not _has_table("financial_borderos"):
        op.create_table(
            "financial_borderos",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("bordero_code", sa.String(length=50), nullable=False),
            sa.Column("bordero_type", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("description", sa.String(length=255), nullable=False),
            sa.Column("bank_account_id", sa.Integer(), nullable=True),
            sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("settled_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("open_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
            sa.Column("created_by_agent", sa.String(length=50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("company_id", "bordero_code", name="uq_financial_borderos_company_code"),
            sa.CheckConstraint("bordero_type IN ('payable', 'receivable')", name="ck_financial_borderos_type"),
            sa.CheckConstraint("status IN ('draft', 'open', 'partially_settled', 'settled', 'cancelled')", name="ck_financial_borderos_status"),
            sa.CheckConstraint("total_amount >= 0", name="ck_financial_borderos_total_nonneg"),
            sa.CheckConstraint("settled_amount >= 0", name="ck_financial_borderos_settled_nonneg"),
            sa.CheckConstraint("open_amount >= 0", name="ck_financial_borderos_open_nonneg"),
        )
    if not _index_exists("financial_borderos", "ix_financial_borderos_company_id"):
        op.create_index("ix_financial_borderos_company_id", "financial_borderos", ["company_id"])
    if not _index_exists("financial_borderos", "ix_financial_borderos_bordero_type"):
        op.create_index("ix_financial_borderos_bordero_type", "financial_borderos", ["bordero_type"])
    if not _index_exists("financial_borderos", "ix_financial_borderos_status"):
        op.create_index("ix_financial_borderos_status", "financial_borderos", ["status"])
    if not _index_exists("financial_borderos", "ix_financial_borderos_bank_account_id"):
        op.create_index("ix_financial_borderos_bank_account_id", "financial_borderos", ["bank_account_id"])

    if not _has_table("financial_bordero_items"):
        op.create_table(
            "financial_bordero_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("bordero_id", sa.Integer(), sa.ForeignKey("financial_borderos.id", ondelete="CASCADE"), nullable=False),
            sa.Column("financial_schedule_id", sa.Integer(), sa.ForeignKey("financial_schedules.id"), nullable=False),
            sa.Column("item_code", sa.String(length=50), nullable=False),
            sa.Column("selected_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("settled_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("open_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("company_id", "bordero_id", "financial_schedule_id", name="uq_financial_bordero_items_schedule"),
            sa.CheckConstraint("selected_amount >= 0", name="ck_financial_bordero_items_selected_nonneg"),
            sa.CheckConstraint("settled_amount >= 0", name="ck_financial_bordero_items_settled_nonneg"),
            sa.CheckConstraint("open_amount >= 0", name="ck_financial_bordero_items_open_nonneg"),
        )
    if not _index_exists("financial_bordero_items", "ix_financial_bordero_items_company_id"):
        op.create_index("ix_financial_bordero_items_company_id", "financial_bordero_items", ["company_id"])
    if not _index_exists("financial_bordero_items", "ix_financial_bordero_items_bordero_id"):
        op.create_index("ix_financial_bordero_items_bordero_id", "financial_bordero_items", ["bordero_id"])
    if not _index_exists("financial_bordero_items", "ix_financial_bordero_items_financial_schedule_id"):
        op.create_index("ix_financial_bordero_items_financial_schedule_id", "financial_bordero_items", ["financial_schedule_id"])

    if not _has_table("financial_bordero_settlements"):
        op.create_table(
            "financial_bordero_settlements",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
            sa.Column("bordero_id", sa.Integer(), sa.ForeignKey("financial_borderos.id", ondelete="CASCADE"), nullable=False),
            sa.Column("settlement_code", sa.String(length=50), nullable=False),
            sa.Column("settlement_status", sa.String(length=30), nullable=False, server_default="posted"),
            sa.Column("settlement_date", sa.Date(), nullable=False),
            sa.Column("bank_account_id", sa.Integer(), nullable=True),
            sa.Column("gross_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("allocated_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("variance_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=True),
            sa.Column("created_by_agent", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("company_id", "settlement_code", name="uq_financial_bordero_settlements_company_code"),
            sa.CheckConstraint("settlement_status IN ('posted', 'cancelled')", name="ck_financial_bordero_settlements_status"),
            sa.CheckConstraint("gross_amount >= 0", name="ck_financial_bordero_settlements_gross_nonneg"),
            sa.CheckConstraint("allocated_amount >= 0", name="ck_financial_bordero_settlements_allocated_nonneg"),
            sa.CheckConstraint("variance_amount >= 0", name="ck_financial_bordero_settlements_variance_nonneg"),
        )
    if not _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_company_id"):
        op.create_index("ix_financial_bordero_settlements_company_id", "financial_bordero_settlements", ["company_id"])
    if not _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_bordero_id"):
        op.create_index("ix_financial_bordero_settlements_bordero_id", "financial_bordero_settlements", ["bordero_id"])
    if not _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_settlement_status"):
        op.create_index("ix_financial_bordero_settlements_settlement_status", "financial_bordero_settlements", ["settlement_status"])
    if not _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_settlement_date"):
        op.create_index("ix_financial_bordero_settlements_settlement_date", "financial_bordero_settlements", ["settlement_date"])
    if not _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_bank_account_id"):
        op.create_index("ix_financial_bordero_settlements_bank_account_id", "financial_bordero_settlements", ["bank_account_id"])


def downgrade():
    if _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_bank_account_id"):
        op.drop_index("ix_financial_bordero_settlements_bank_account_id", table_name="financial_bordero_settlements")
    if _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_settlement_date"):
        op.drop_index("ix_financial_bordero_settlements_settlement_date", table_name="financial_bordero_settlements")
    if _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_settlement_status"):
        op.drop_index("ix_financial_bordero_settlements_settlement_status", table_name="financial_bordero_settlements")
    if _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_bordero_id"):
        op.drop_index("ix_financial_bordero_settlements_bordero_id", table_name="financial_bordero_settlements")
    if _index_exists("financial_bordero_settlements", "ix_financial_bordero_settlements_company_id"):
        op.drop_index("ix_financial_bordero_settlements_company_id", table_name="financial_bordero_settlements")
    if _has_table("financial_bordero_settlements"):
        op.drop_table("financial_bordero_settlements")

    if _index_exists("financial_bordero_items", "ix_financial_bordero_items_financial_schedule_id"):
        op.drop_index("ix_financial_bordero_items_financial_schedule_id", table_name="financial_bordero_items")
    if _index_exists("financial_bordero_items", "ix_financial_bordero_items_bordero_id"):
        op.drop_index("ix_financial_bordero_items_bordero_id", table_name="financial_bordero_items")
    if _index_exists("financial_bordero_items", "ix_financial_bordero_items_company_id"):
        op.drop_index("ix_financial_bordero_items_company_id", table_name="financial_bordero_items")
    if _has_table("financial_bordero_items"):
        op.drop_table("financial_bordero_items")

    if _index_exists("financial_borderos", "ix_financial_borderos_bank_account_id"):
        op.drop_index("ix_financial_borderos_bank_account_id", table_name="financial_borderos")
    if _index_exists("financial_borderos", "ix_financial_borderos_status"):
        op.drop_index("ix_financial_borderos_status", table_name="financial_borderos")
    if _index_exists("financial_borderos", "ix_financial_borderos_bordero_type"):
        op.drop_index("ix_financial_borderos_bordero_type", table_name="financial_borderos")
    if _index_exists("financial_borderos", "ix_financial_borderos_company_id"):
        op.drop_index("ix_financial_borderos_company_id", table_name="financial_borderos")
    if _has_table("financial_borderos"):
        op.drop_table("financial_borderos")
