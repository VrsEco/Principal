"""create additional financial catalogs

Revision ID: 20260319_0400
Revises: 20260319_0300
Create Date: 2026-03-19 04:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0400"
down_revision = "20260319_0300"
branch_labels = None
depends_on = None


def _create_simple_catalog_table(table_name: str, uq_name: str):
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name=uq_name),
    )
    op.create_index(f"ix_{table_name}_company_id", table_name, ["company_id"])
    op.create_index(f"ix_{table_name}_is_active", table_name, ["is_active"])


def _drop_simple_catalog_table(table_name: str):
    op.drop_index(f"ix_{table_name}_is_active", table_name=table_name)
    op.drop_index(f"ix_{table_name}_company_id", table_name=table_name)
    op.drop_table(table_name)


def upgrade():
    _create_simple_catalog_table("financial_account_categories", "uq_financial_account_categories_company_code")
    _create_simple_catalog_table("financial_payment_terms", "uq_financial_payment_terms_company_code")
    _create_simple_catalog_table("financial_asset_accounts", "uq_financial_asset_accounts_company_code")
    _create_simple_catalog_table("financial_correction_indexes", "uq_financial_correction_indexes_company_code")
    _create_simple_catalog_table("financial_discount_rules", "uq_financial_discount_rules_company_code")
    _create_simple_catalog_table("financial_payment_methods", "uq_financial_payment_methods_company_code")


def downgrade():
    _drop_simple_catalog_table("financial_payment_methods")
    _drop_simple_catalog_table("financial_discount_rules")
    _drop_simple_catalog_table("financial_correction_indexes")
    _drop_simple_catalog_table("financial_asset_accounts")
    _drop_simple_catalog_table("financial_payment_terms")
    _drop_simple_catalog_table("financial_account_categories")
