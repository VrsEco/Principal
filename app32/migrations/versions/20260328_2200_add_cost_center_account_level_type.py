"""add analytic/synthetic structure to financial cost centers

Revision ID: 20260328_2200
Revises: 20260328_2100
Create Date: 2026-03-28 22:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260328_2200"
down_revision = "20260328_2100"
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


def upgrade():
    if _has_table("financial_cost_centers") and not _has_column("financial_cost_centers", "accepts_posting"):
        op.add_column(
            "financial_cost_centers",
            sa.Column("accepts_posting", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if _has_table("financial_cost_centers"):
        op.execute(
            """
            UPDATE financial_cost_centers
               SET metadata_json = jsonb_set(
                   COALESCE(metadata_json, '{}'::jsonb),
                   '{account_level_type}',
                   to_jsonb(CASE WHEN accepts_posting THEN 'analytic'::text ELSE 'synthetic'::text END),
                   true
               )
             WHERE COALESCE(metadata_json, '{}'::jsonb) ->> 'account_level_type' IS NULL
            """
        )


def downgrade():
    if _has_table("financial_cost_centers") and _has_column("financial_cost_centers", "accepts_posting"):
        op.drop_column("financial_cost_centers", "accepts_posting")
