"""create_instruction_registry_tables

Revision ID: 20260517_1200
Revises: 20260507_1100
Create Date: 2026-05-17 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260517_1200"
down_revision = "20260507_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "instruction_registry_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=24), nullable=False),
        sa.Column("runtime_profile", sa.String(length=80), nullable=False),
        sa.Column("agent_key", sa.String(length=80), nullable=True),
        sa.Column("harness_key", sa.String(length=120), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rollout_status", sa.String(length=30), nullable=False),
        sa.Column("entry_version", sa.String(length=40), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("invalidation_token", sa.String(length=64), nullable=False),
        sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_invalidated_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_instruction_registry_entries_scope_type"), "instruction_registry_entries", ["scope_type"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_runtime_profile"), "instruction_registry_entries", ["runtime_profile"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_agent_key"), "instruction_registry_entries", ["agent_key"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_harness_key"), "instruction_registry_entries", ["harness_key"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_company_id"), "instruction_registry_entries", ["company_id"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_channel"), "instruction_registry_entries", ["channel"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_environment"), "instruction_registry_entries", ["environment"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_status"), "instruction_registry_entries", ["status"], unique=False)
    op.create_index(op.f("ix_instruction_registry_entries_rollout_status"), "instruction_registry_entries", ["rollout_status"], unique=False)

    op.create_table(
        "instruction_registry_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entry_id"], ["instruction_registry_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_instruction_registry_audit_logs_entry_id"), "instruction_registry_audit_logs", ["entry_id"], unique=False)
    op.create_index(op.f("ix_instruction_registry_audit_logs_company_id"), "instruction_registry_audit_logs", ["company_id"], unique=False)
    op.create_index(op.f("ix_instruction_registry_audit_logs_actor_user_id"), "instruction_registry_audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_instruction_registry_audit_logs_event_type"), "instruction_registry_audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_instruction_registry_audit_logs_result"), "instruction_registry_audit_logs", ["result"], unique=False)
    op.create_index(op.f("ix_instruction_registry_audit_logs_created_at"), "instruction_registry_audit_logs", ["created_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_instruction_registry_audit_logs_created_at"), table_name="instruction_registry_audit_logs")
    op.drop_index(op.f("ix_instruction_registry_audit_logs_result"), table_name="instruction_registry_audit_logs")
    op.drop_index(op.f("ix_instruction_registry_audit_logs_event_type"), table_name="instruction_registry_audit_logs")
    op.drop_index(op.f("ix_instruction_registry_audit_logs_actor_user_id"), table_name="instruction_registry_audit_logs")
    op.drop_index(op.f("ix_instruction_registry_audit_logs_company_id"), table_name="instruction_registry_audit_logs")
    op.drop_index(op.f("ix_instruction_registry_audit_logs_entry_id"), table_name="instruction_registry_audit_logs")
    op.drop_table("instruction_registry_audit_logs")

    op.drop_index(op.f("ix_instruction_registry_entries_rollout_status"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_status"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_environment"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_channel"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_company_id"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_harness_key"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_agent_key"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_runtime_profile"), table_name="instruction_registry_entries")
    op.drop_index(op.f("ix_instruction_registry_entries_scope_type"), table_name="instruction_registry_entries")
    op.drop_table("instruction_registry_entries")
