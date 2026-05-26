"""add contract financial satellites

Revision ID: 20260526_1700
Revises: 20260526_1500
Create Date: 2026-05-26 17:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260526_1700"
down_revision = "20260526_1500"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade():
    if _has_table("contract_financial_terms"):
        if not _has_column("contract_financial_terms", "default_chart_account_id"):
            op.add_column("contract_financial_terms", sa.Column("default_chart_account_id", sa.Integer(), nullable=True))
            op.create_index(
                "ix_contract_financial_terms_default_chart_account_id",
                "contract_financial_terms",
                ["default_chart_account_id"],
            )
        if not _has_column("contract_financial_terms", "default_cost_center_id"):
            op.add_column("contract_financial_terms", sa.Column("default_cost_center_id", sa.Integer(), nullable=True))
            op.create_index(
                "ix_contract_financial_terms_default_cost_center_id",
                "contract_financial_terms",
                ["default_cost_center_id"],
            )

    if not _has_table("financial_satellite_policies"):
        op.create_table(
            "financial_satellite_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("contract_id", sa.Integer(), nullable=True),
            sa.Column("policy_code", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("satellite_nature", sa.String(length=40), nullable=False),
            sa.Column("principal_effect_mode", sa.String(length=50), nullable=False, server_default="none"),
            sa.Column("satellite_effect_mode", sa.String(length=50), nullable=False, server_default="open_until_manual"),
            sa.Column("trigger_event", sa.String(length=40), nullable=False, server_default="on_manual_release"),
            sa.Column("settlement_scope", sa.String(length=30), nullable=False, server_default="full"),
            sa.Column("auto_apply", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("bank_account_id", sa.Integer(), nullable=True),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
            sa.ForeignKeyConstraint(["bank_account_id"], ["financial_bank_accounts.id"]),
            sa.ForeignKeyConstraint(["chart_account_id"], ["financial_chart_accounts.id"]),
            sa.UniqueConstraint("company_id", "policy_code", name="uq_financial_satellite_policies_company_code"),
        )
        op.create_index("ix_financial_satellite_policies_company_id", "financial_satellite_policies", ["company_id"])
        op.create_index("ix_financial_satellite_policies_contract_id", "financial_satellite_policies", ["contract_id"])
        op.create_index("ix_financial_satellite_policies_satellite_nature", "financial_satellite_policies", ["satellite_nature"])

    if not _has_table("financial_schedule_links"):
        op.create_table(
            "financial_schedule_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("parent_schedule_id", sa.Integer(), nullable=False),
            sa.Column("child_schedule_id", sa.Integer(), nullable=False),
            sa.Column("policy_id", sa.Integer(), nullable=True),
            sa.Column("link_type", sa.String(length=30), nullable=False, server_default="satellite"),
            sa.Column("title_nature", sa.String(length=40), nullable=False),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["parent_schedule_id"], ["financial_schedules.id"]),
            sa.ForeignKeyConstraint(["child_schedule_id"], ["financial_schedules.id"]),
            sa.ForeignKeyConstraint(["policy_id"], ["financial_satellite_policies.id"]),
            sa.UniqueConstraint(
                "company_id",
                "parent_schedule_id",
                "child_schedule_id",
                name="uq_financial_schedule_links_company_parent_child",
            ),
        )
        op.create_index("ix_financial_schedule_links_company_id", "financial_schedule_links", ["company_id"])
        op.create_index("ix_financial_schedule_links_parent_schedule_id", "financial_schedule_links", ["parent_schedule_id"])
        op.create_index("ix_financial_schedule_links_child_schedule_id", "financial_schedule_links", ["child_schedule_id"])

    if not _has_table("financial_satellite_executions"):
        op.create_table(
            "financial_satellite_executions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("policy_id", sa.Integer(), nullable=False),
            sa.Column("parent_schedule_id", sa.Integer(), nullable=False),
            sa.Column("child_schedule_id", sa.Integer(), nullable=False),
            sa.Column("trigger_settlement_id", sa.Integer(), nullable=True),
            sa.Column("parent_compensation_settlement_id", sa.Integer(), nullable=True),
            sa.Column("child_settlement_id", sa.Integer(), nullable=True),
            sa.Column("trigger_event", sa.String(length=40), nullable=False),
            sa.Column("executed_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("execution_status", sa.String(length=30), nullable=False, server_default="success"),
            sa.Column("executed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("reversed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["policy_id"], ["financial_satellite_policies.id"]),
            sa.ForeignKeyConstraint(["parent_schedule_id"], ["financial_schedules.id"]),
            sa.ForeignKeyConstraint(["child_schedule_id"], ["financial_schedules.id"]),
            sa.ForeignKeyConstraint(["trigger_settlement_id"], ["financial_settlements.id"]),
            sa.ForeignKeyConstraint(["parent_compensation_settlement_id"], ["financial_settlements.id"]),
            sa.ForeignKeyConstraint(["child_settlement_id"], ["financial_settlements.id"]),
            sa.UniqueConstraint(
                "company_id",
                "policy_id",
                "child_schedule_id",
                "trigger_settlement_id",
                "trigger_event",
                name="uq_financial_satellite_exec_company_policy_child_trigger",
            ),
        )
        op.create_index("ix_financial_satellite_executions_company_id", "financial_satellite_executions", ["company_id"])
        op.create_index("ix_financial_satellite_executions_policy_id", "financial_satellite_executions", ["policy_id"])
        op.create_index("ix_financial_satellite_executions_parent_schedule_id", "financial_satellite_executions", ["parent_schedule_id"])
        op.create_index("ix_financial_satellite_executions_child_schedule_id", "financial_satellite_executions", ["child_schedule_id"])


def downgrade():
    if _has_table("financial_satellite_executions"):
        op.drop_table("financial_satellite_executions")
    if _has_table("financial_schedule_links"):
        op.drop_table("financial_schedule_links")
    if _has_table("financial_satellite_policies"):
        op.drop_table("financial_satellite_policies")
    if _has_table("contract_financial_terms"):
        if _has_column("contract_financial_terms", "default_cost_center_id"):
            op.drop_column("contract_financial_terms", "default_cost_center_id")
        if _has_column("contract_financial_terms", "default_chart_account_id"):
            op.drop_column("contract_financial_terms", "default_chart_account_id")
