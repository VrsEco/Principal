"""create financial budget matrix

Revision ID: 20260322_0900
Revises: 20260317_0905, 20260320_2345
Create Date: 2026-03-22 09:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260322_0900"
down_revision = ("20260317_0905", "20260320_2345")
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
    if not _has_table("financial_budget_versions"):
        op.create_table(
            "financial_budget_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("scenario_type", sa.String(length=20), nullable=False, server_default="original"),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "status IN ('draft', 'active', 'archived')",
                name="ck_financial_budget_versions_status",
            ),
            sa.CheckConstraint(
                "scenario_type IN ('original', 'forecast', 'reforecast')",
                name="ck_financial_budget_versions_scenario_type",
            ),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "code", name="uq_financial_budget_versions_company_code"),
        )

    if not _has_table("financial_budget_lines"):
        op.create_table(
            "financial_budget_lines",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("budget_version_id", sa.Integer(), nullable=False),
            sa.Column("line_code", sa.String(length=60), nullable=False),
            sa.Column("line_name", sa.String(length=160), nullable=False),
            sa.Column("line_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("budget_view", sa.String(length=20), nullable=False, server_default="competence"),
            sa.Column("movement_nature", sa.String(length=10), nullable=False, server_default="debit"),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("process_instance_id", sa.Integer(), nullable=True),
            sa.Column("routine_id", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "budget_view IN ('competence', 'due', 'cash')",
                name="ck_financial_budget_lines_budget_view",
            ),
            sa.CheckConstraint(
                "movement_nature IN ('debit', 'credit')",
                name="ck_financial_budget_lines_movement_nature",
            ),
            sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
            sa.ForeignKeyConstraint(["budget_version_id"], ["financial_budget_versions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["chart_account_id"], ["financial_chart_accounts.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["cost_center_id"], ["financial_cost_centers.id"]),
            sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
            sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "budget_version_id", "line_code", name="uq_financial_budget_lines_version_code"),
        )

    if not _has_table("financial_budget_amounts"):
        op.create_table(
            "financial_budget_amounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("budget_line_id", sa.Integer(), nullable=False),
            sa.Column("period_month", sa.Date(), nullable=False),
            sa.Column("budget_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["budget_line_id"], ["financial_budget_lines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "budget_line_id", "period_month", name="uq_financial_budget_amounts_line_period"),
        )

    indexes = [
        ("idx_financial_budget_versions_company_status", "financial_budget_versions", ["company_id", "status"]),
        ("idx_financial_budget_versions_company_period", "financial_budget_versions", ["company_id", "period_start", "period_end"]),
        ("idx_financial_budget_versions_company_scenario", "financial_budget_versions", ["company_id", "scenario_type"]),
        ("idx_financial_budget_lines_company_version", "financial_budget_lines", ["company_id", "budget_version_id"]),
        ("idx_financial_budget_lines_company_chart", "financial_budget_lines", ["company_id", "chart_account_id"]),
        ("idx_financial_budget_lines_company_cost_center", "financial_budget_lines", ["company_id", "cost_center_id"]),
        ("idx_financial_budget_amounts_company_line", "financial_budget_amounts", ["company_id", "budget_line_id"]),
        ("idx_financial_budget_amounts_company_period", "financial_budget_amounts", ["company_id", "period_month"]),
    ]

    for index_name, table_name, columns in indexes:
        if _has_table(table_name) and not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_budget_amounts_company_period", "financial_budget_amounts"),
        ("idx_financial_budget_amounts_company_line", "financial_budget_amounts"),
        ("idx_financial_budget_lines_company_cost_center", "financial_budget_lines"),
        ("idx_financial_budget_lines_company_chart", "financial_budget_lines"),
        ("idx_financial_budget_lines_company_version", "financial_budget_lines"),
        ("idx_financial_budget_versions_company_scenario", "financial_budget_versions"),
        ("idx_financial_budget_versions_company_period", "financial_budget_versions"),
        ("idx_financial_budget_versions_company_status", "financial_budget_versions"),
    ]:
        if inspector.has_table(table_name) and _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
            inspector = sa.inspect(bind)

    if inspector.has_table("financial_budget_amounts"):
        op.drop_table("financial_budget_amounts")
        inspector = sa.inspect(bind)
    if inspector.has_table("financial_budget_lines"):
        op.drop_table("financial_budget_lines")
        inspector = sa.inspect(bind)
    if inspector.has_table("financial_budget_versions"):
        op.drop_table("financial_budget_versions")
