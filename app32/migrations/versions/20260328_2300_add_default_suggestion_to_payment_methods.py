"""add default suggestion flag to financial payment methods

Revision ID: 20260328_2300
Revises: 20260328_2200
Create Date: 2026-03-28 23:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260328_2300"
down_revision = "20260328_2200"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    if _has_table("financial_payment_methods") and not _has_column("financial_payment_methods", "is_default_suggestion"):
        op.add_column(
            "financial_payment_methods",
            sa.Column("is_default_suggestion", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if _has_table("financial_payment_methods") and not _index_exists(
        "financial_payment_methods",
        "ix_financial_payment_methods_is_default_suggestion",
    ):
        op.create_index(
            "ix_financial_payment_methods_is_default_suggestion",
            "financial_payment_methods",
            ["is_default_suggestion"],
        )


def downgrade():
    if _has_table("financial_payment_methods") and _index_exists(
        "financial_payment_methods",
        "ix_financial_payment_methods_is_default_suggestion",
    ):
        op.drop_index(
            "ix_financial_payment_methods_is_default_suggestion",
            table_name="financial_payment_methods",
        )
    if _has_table("financial_payment_methods") and _has_column("financial_payment_methods", "is_default_suggestion"):
        op.drop_column("financial_payment_methods", "is_default_suggestion")
