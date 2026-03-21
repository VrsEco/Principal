"""create financial catalogs

Revision ID: 20260319_0100
Revises: 20260319_0045
Create Date: 2026-03-19 01:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0100"
down_revision = "20260319_0045"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("bank_code", sa.String(length=20)),
        sa.Column("bank_name", sa.String(length=120)),
        sa.Column("branch_number", sa.String(length=20)),
        sa.Column("account_number", sa.String(length=30)),
        sa.Column("account_digit", sa.String(length=10)),
        sa.Column("holder_name", sa.String(length=255)),
        sa.Column("holder_document", sa.String(length=50)),
        sa.Column("pix_key", sa.String(length=120)),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.UniqueConstraint("company_id", "code", name="uq_financial_bank_accounts_company_code"),
    )
    op.create_index("ix_financial_bank_accounts_company_id", "financial_bank_accounts", ["company_id"])
    op.create_index("ix_financial_bank_accounts_is_active", "financial_bank_accounts", ["is_active"])

    op.create_table(
        "financial_chart_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("financial_chart_accounts.id")),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_kind", sa.String(length=20), nullable=False, server_default="expense"),
        sa.Column("movement_nature", sa.String(length=10)),
        sa.Column("accepts_posting", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.CheckConstraint("account_kind IN ('asset', 'liability', 'equity', 'revenue', 'expense', 'result')", name="ck_financial_chart_accounts_kind"),
        sa.UniqueConstraint("company_id", "code", name="uq_financial_chart_accounts_company_code"),
    )
    op.create_index("ix_financial_chart_accounts_company_id", "financial_chart_accounts", ["company_id"])
    op.create_index("ix_financial_chart_accounts_parent_id", "financial_chart_accounts", ["parent_id"])
    op.create_index("ix_financial_chart_accounts_is_active", "financial_chart_accounts", ["is_active"])

    op.create_table(
        "financial_cost_centers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("financial_cost_centers.id")),
        sa.Column("manager_employee_id", sa.Integer(), sa.ForeignKey("employees.id")),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.UniqueConstraint("company_id", "code", name="uq_financial_cost_centers_company_code"),
    )
    op.create_index("ix_financial_cost_centers_company_id", "financial_cost_centers", ["company_id"])
    op.create_index("ix_financial_cost_centers_parent_id", "financial_cost_centers", ["parent_id"])
    op.create_index("ix_financial_cost_centers_is_active", "financial_cost_centers", ["is_active"])

    op.create_table(
        "financial_counterparties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("default_chart_account_id", sa.Integer(), sa.ForeignKey("financial_chart_accounts.id")),
        sa.Column("default_cost_center_id", sa.Integer(), sa.ForeignKey("financial_cost_centers.id")),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("legal_name", sa.String(length=255)),
        sa.Column("document_number", sa.String(length=50)),
        sa.Column("email", sa.String(length=255)),
        sa.Column("phone", sa.String(length=50)),
        sa.Column("pix_key", sa.String(length=120)),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.UniqueConstraint("company_id", "code", name="uq_financial_counterparties_company_code"),
    )
    op.create_index("ix_financial_counterparties_company_id", "financial_counterparties", ["company_id"])
    op.create_index("ix_financial_counterparties_document_number", "financial_counterparties", ["document_number"])
    op.create_index("ix_financial_counterparties_is_active", "financial_counterparties", ["is_active"])


def downgrade():
    op.drop_index("ix_financial_counterparties_is_active", table_name="financial_counterparties")
    op.drop_index("ix_financial_counterparties_document_number", table_name="financial_counterparties")
    op.drop_index("ix_financial_counterparties_company_id", table_name="financial_counterparties")
    op.drop_table("financial_counterparties")

    op.drop_index("ix_financial_cost_centers_is_active", table_name="financial_cost_centers")
    op.drop_index("ix_financial_cost_centers_parent_id", table_name="financial_cost_centers")
    op.drop_index("ix_financial_cost_centers_company_id", table_name="financial_cost_centers")
    op.drop_table("financial_cost_centers")

    op.drop_index("ix_financial_chart_accounts_is_active", table_name="financial_chart_accounts")
    op.drop_index("ix_financial_chart_accounts_parent_id", table_name="financial_chart_accounts")
    op.drop_index("ix_financial_chart_accounts_company_id", table_name="financial_chart_accounts")
    op.drop_table("financial_chart_accounts")

    op.drop_index("ix_financial_bank_accounts_is_active", table_name="financial_bank_accounts")
    op.drop_index("ix_financial_bank_accounts_company_id", table_name="financial_bank_accounts")
    op.drop_table("financial_bank_accounts")
