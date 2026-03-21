"""create financial automation rules

Revision ID: 20260319_0230
Revises: 20260319_0200
Create Date: 2026-03-19 02:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0230"
down_revision = "20260319_0200"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_automation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("rule_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("trigger_status", sa.String(length=20), nullable=False, server_default="any"),
        sa.Column("trigger_on_create", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_activate_schedule", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule_name_template", sa.String(length=160), nullable=False),
        sa.Column("description_template", sa.String(length=255), nullable=False),
        sa.Column("entry_type", sa.String(length=30), nullable=False, server_default="forecast"),
        sa.Column("movement_nature", sa.String(length=10), nullable=False),
        sa.Column("origin_type", sa.String(length=30), nullable=False, server_default="process"),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="one_time"),
        sa.Column("interval_value", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_offset_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_offset_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("template_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("auto_post", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generate_advance_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bank_account_id", sa.Integer(), nullable=True),
        sa.Column("counterparty_id", sa.Integer(), nullable=True),
        sa.Column("chart_account_id", sa.Integer(), nullable=True),
        sa.Column("cost_center_id", sa.Integer(), nullable=True),
        sa.Column("routine_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_execution_at", sa.DateTime(), nullable=True),
        sa.Column("last_generated_schedule_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["last_generated_schedule_id"], ["financial_schedules.id"]),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "rule_code", name="uq_financial_automation_rules_company_code"),
        sa.CheckConstraint(
            "entry_type IN ('payable', 'receivable', 'bank_movement', 'transfer', 'adjustment', 'forecast')",
            name="ck_financial_automation_rules_entry_type",
        ),
        sa.CheckConstraint("movement_nature IN ('debit', 'credit')", name="ck_financial_automation_rules_movement_nature"),
        sa.CheckConstraint(
            "origin_type IN ('manual', 'process', 'routine', 'sapiens', 'ofx', 'csv', 'xls', 'csc', 'api', 'mcp', 'migration')",
            name="ck_financial_automation_rules_origin_type",
        ),
        sa.CheckConstraint(
            "frequency IN ('one_time', 'weekly', 'monthly', 'yearly')",
            name="ck_financial_automation_rules_frequency",
        ),
        sa.CheckConstraint(
            "trigger_status IN ('pending', 'in_progress', 'completed', 'overdue', 'any')",
            name="ck_financial_automation_rules_trigger_status",
        ),
        sa.CheckConstraint("template_amount >= 0", name="ck_financial_automation_rules_amount_nonneg"),
        sa.CheckConstraint("interval_value >= 1", name="ck_financial_automation_rules_interval_positive"),
    )
    op.create_index("ix_financial_automation_rules_company_id", "financial_automation_rules", ["company_id"])
    op.create_index("ix_financial_automation_rules_process_id", "financial_automation_rules", ["process_id"])
    op.create_index("ix_financial_automation_rules_activity_id", "financial_automation_rules", ["activity_id"])
    op.create_index("ix_financial_automation_rules_trigger_status", "financial_automation_rules", ["trigger_status"])
    op.create_index("ix_financial_automation_rules_is_active", "financial_automation_rules", ["is_active"])


def downgrade():
    op.drop_index("ix_financial_automation_rules_is_active", table_name="financial_automation_rules")
    op.drop_index("ix_financial_automation_rules_trigger_status", table_name="financial_automation_rules")
    op.drop_index("ix_financial_automation_rules_activity_id", table_name="financial_automation_rules")
    op.drop_index("ix_financial_automation_rules_process_id", table_name="financial_automation_rules")
    op.drop_index("ix_financial_automation_rules_company_id", table_name="financial_automation_rules")
    op.drop_table("financial_automation_rules")
