"""add default suggestion flags for financial collaborators

Revision ID: 20260328_0900
Revises: 20260327_1400
Create Date: 2026-03-28 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260328_0900"
down_revision = "20260327_1400"
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
    if _has_table("financial_cost_centers") and not _has_column("financial_cost_centers", "is_default_suggestion"):
        op.add_column(
            "financial_cost_centers",
            sa.Column("is_default_suggestion", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if _has_table("financial_cost_centers") and not _index_exists(
        "financial_cost_centers", "ix_financial_cost_centers_is_default_suggestion"
    ):
        op.create_index(
            "ix_financial_cost_centers_is_default_suggestion",
            "financial_cost_centers",
            ["is_default_suggestion"],
        )

    if _has_table("financial_domain_enablements") and not _has_column("financial_domain_enablements", "is_default_suggestion"):
        op.add_column(
            "financial_domain_enablements",
            sa.Column("is_default_suggestion", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if _has_table("financial_domain_enablements") and not _index_exists(
        "financial_domain_enablements", "ix_financial_domain_enablements_is_default_suggestion"
    ):
        op.create_index(
            "ix_financial_domain_enablements_is_default_suggestion",
            "financial_domain_enablements",
            ["is_default_suggestion"],
        )

    if _has_table("financial_budget_documents") and not _has_column("financial_budget_documents", "is_default_suggestion"):
        op.add_column(
            "financial_budget_documents",
            sa.Column("is_default_suggestion", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if _has_table("financial_budget_documents") and not _index_exists(
        "financial_budget_documents", "ix_financial_budget_documents_is_default_suggestion"
    ):
        op.create_index(
            "ix_financial_budget_documents_is_default_suggestion",
            "financial_budget_documents",
            ["is_default_suggestion"],
        )


def downgrade():
    if _has_table("financial_budget_documents") and _index_exists(
        "financial_budget_documents", "ix_financial_budget_documents_is_default_suggestion"
    ):
        op.drop_index("ix_financial_budget_documents_is_default_suggestion", table_name="financial_budget_documents")
    if _has_table("financial_budget_documents") and _has_column("financial_budget_documents", "is_default_suggestion"):
        op.drop_column("financial_budget_documents", "is_default_suggestion")

    if _has_table("financial_domain_enablements") and _index_exists(
        "financial_domain_enablements", "ix_financial_domain_enablements_is_default_suggestion"
    ):
        op.drop_index("ix_financial_domain_enablements_is_default_suggestion", table_name="financial_domain_enablements")
    if _has_table("financial_domain_enablements") and _has_column("financial_domain_enablements", "is_default_suggestion"):
        op.drop_column("financial_domain_enablements", "is_default_suggestion")

    if _has_table("financial_cost_centers") and _index_exists(
        "financial_cost_centers", "ix_financial_cost_centers_is_default_suggestion"
    ):
        op.drop_index("ix_financial_cost_centers_is_default_suggestion", table_name="financial_cost_centers")
    if _has_table("financial_cost_centers") and _has_column("financial_cost_centers", "is_default_suggestion"):
        op.drop_column("financial_cost_centers", "is_default_suggestion")
