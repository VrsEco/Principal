"""create financial schedules

Revision ID: 20260319_0200
Revises: 20260319_0130
Create Date: 2026-03-19 02:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0200"
down_revision = "20260319_0130"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("schedule_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("entry_type", sa.String(length=30), nullable=False),
        sa.Column("movement_nature", sa.String(length=10), nullable=False),
        sa.Column("origin_type", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="monthly"),
        sa.Column("interval_value", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("document_number_prefix", sa.String(length=40), nullable=True),
        sa.Column("template_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("auto_post", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generate_advance_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bank_account_id", sa.Integer(), nullable=True),
        sa.Column("counterparty_id", sa.Integer(), nullable=True),
        sa.Column("chart_account_id", sa.Integer(), nullable=True),
        sa.Column("cost_center_id", sa.Integer(), nullable=True),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("process_instance_id", sa.Integer(), nullable=True),
        sa.Column("routine_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_employee_id", sa.Integer(), nullable=True),
        sa.Column("created_by_agent", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("last_generated_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by_employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["last_generated_entry_id"], ["financial_entries.id"]),
        sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
        sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "schedule_code", name="uq_financial_schedules_company_code"),
        sa.CheckConstraint(
            "entry_type IN ('payable', 'receivable', 'bank_movement', 'transfer', 'adjustment', 'forecast')",
            name="ck_financial_schedules_entry_type",
        ),
        sa.CheckConstraint("movement_nature IN ('debit', 'credit')", name="ck_financial_schedules_movement_nature"),
        sa.CheckConstraint(
            "origin_type IN ('manual', 'process', 'routine', 'sapiens', 'ofx', 'csv', 'xls', 'csc', 'api', 'mcp', 'migration')",
            name="ck_financial_schedules_origin_type",
        ),
        sa.CheckConstraint(
            "frequency IN ('one_time', 'weekly', 'monthly', 'yearly')",
            name="ck_financial_schedules_frequency",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed', 'cancelled')",
            name="ck_financial_schedules_status",
        ),
        sa.CheckConstraint("template_amount >= 0", name="ck_financial_schedules_amount_nonneg"),
        sa.CheckConstraint("interval_value >= 1", name="ck_financial_schedules_interval_positive"),
    )
    op.create_index("ix_financial_schedules_company_id", "financial_schedules", ["company_id"])
    op.create_index("ix_financial_schedules_status", "financial_schedules", ["status"])
    op.create_index("ix_financial_schedules_frequency", "financial_schedules", ["frequency"])
    op.create_index("ix_financial_schedules_start_date", "financial_schedules", ["start_date"])
    op.create_index("ix_financial_schedules_next_due_date", "financial_schedules", ["next_due_date"])
    op.create_index("ix_financial_schedules_activity_id", "financial_schedules", ["activity_id"])
    op.create_index("ix_financial_schedules_process_instance_id", "financial_schedules", ["process_instance_id"])
    op.create_index("ix_financial_schedules_routine_id", "financial_schedules", ["routine_id"])


def downgrade():
    op.drop_index("ix_financial_schedules_routine_id", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_process_instance_id", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_activity_id", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_next_due_date", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_start_date", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_frequency", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_status", table_name="financial_schedules")
    op.drop_index("ix_financial_schedules_company_id", table_name="financial_schedules")
    op.drop_table("financial_schedules")
