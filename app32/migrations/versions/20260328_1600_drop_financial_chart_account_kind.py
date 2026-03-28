"""drop financial chart account kind

Revision ID: 20260328_1600
Revises: 20260328_1000
Create Date: 2026-03-28 16:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260328_1600"
down_revision = "20260328_1000"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("financial_chart_accounts")}
    columns = {column["name"] for column in inspector.get_columns("financial_chart_accounts")}

    if "ix_financial_chart_accounts_account_kind" in indexes:
        op.drop_index("ix_financial_chart_accounts_account_kind", table_name="financial_chart_accounts")

    op.drop_constraint("ck_financial_chart_accounts_kind", "financial_chart_accounts", type_="check")

    if "account_kind" in columns:
        op.drop_column("financial_chart_accounts", "account_kind")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("financial_chart_accounts")}
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("financial_chart_accounts")}
    indexes = {index["name"] for index in inspector.get_indexes("financial_chart_accounts")}

    if "account_kind" not in columns:
        op.add_column(
            "financial_chart_accounts",
            sa.Column("account_kind", sa.String(length=20), nullable=False, server_default="expense"),
        )

    if "ck_financial_chart_accounts_kind" not in checks:
        op.create_check_constraint(
            "ck_financial_chart_accounts_kind",
            "financial_chart_accounts",
            "account_kind IN ('asset', 'liability', 'equity', 'revenue', 'expense', 'result')",
        )

    if "ix_financial_chart_accounts_account_kind" not in indexes:
        op.create_index(
            "ix_financial_chart_accounts_account_kind",
            "financial_chart_accounts",
            ["account_kind"],
        )
