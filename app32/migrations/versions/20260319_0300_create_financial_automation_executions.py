"""create financial automation executions

Revision ID: 20260319_0300
Revises: 20260319_0230
Create Date: 2026-03-19 03:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0300"
down_revision = "20260319_0230"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_automation_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("process_instance_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("trigger_status", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("execution_status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("executed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["financial_automation_rules.id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["financial_schedules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "rule_id", "process_instance_id", "idempotency_key", "attempt_number", name="uq_financial_automation_executions_idempotency"),
        sa.CheckConstraint("execution_status IN ('success', 'skipped', 'error')", name="ck_financial_automation_executions_status"),
        sa.CheckConstraint("attempt_number >= 1", name="ck_financial_automation_executions_attempt_positive"),
    )
    op.create_index("ix_financial_automation_executions_company_id", "financial_automation_executions", ["company_id"])
    op.create_index("ix_financial_automation_executions_rule_id", "financial_automation_executions", ["rule_id"])
    op.create_index("ix_financial_automation_executions_process_instance_id", "financial_automation_executions", ["process_instance_id"])
    op.create_index("ix_financial_automation_executions_trigger_status", "financial_automation_executions", ["trigger_status"])
    op.create_index("ix_financial_automation_executions_execution_status", "financial_automation_executions", ["execution_status"])
    op.create_index("ix_financial_automation_executions_executed_at", "financial_automation_executions", ["executed_at"])


def downgrade():
    op.drop_index("ix_financial_automation_executions_executed_at", table_name="financial_automation_executions")
    op.drop_index("ix_financial_automation_executions_execution_status", table_name="financial_automation_executions")
    op.drop_index("ix_financial_automation_executions_trigger_status", table_name="financial_automation_executions")
    op.drop_index("ix_financial_automation_executions_process_instance_id", table_name="financial_automation_executions")
    op.drop_index("ix_financial_automation_executions_rule_id", table_name="financial_automation_executions")
    op.drop_index("ix_financial_automation_executions_company_id", table_name="financial_automation_executions")
    op.drop_table("financial_automation_executions")
