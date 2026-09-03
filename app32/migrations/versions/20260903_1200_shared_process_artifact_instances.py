"""shared process artifact instances and interaction audit

Revision ID: 20260903_1200
Revises: 20260901_1900
Create Date: 2026-09-03 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260903_1200"
down_revision = "20260901_1900"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "process_activity_artifact_definitions",
        sa.Column("execution_scope", sa.String(length=30), nullable=False, server_default="activity"),
    )
    op.create_check_constraint(
        "ck_process_artifact_definition_execution_scope",
        "process_activity_artifact_definitions",
        "execution_scope IN ('activity', 'process_instance')",
    )
    op.create_index(
        "ix_process_activity_artifact_definitions_execution_scope",
        "process_activity_artifact_definitions",
        ["execution_scope"],
        unique=False,
    )
    op.add_column(
        "process_activity_artifact_executions",
        sa.Column("scope_key", sa.String(length=255), nullable=True),
    )
    op.execute(
        "UPDATE process_activity_artifact_executions "
        "SET scope_key = 'activity:' || activity_execution_id::text WHERE scope_key IS NULL"
    )
    op.alter_column("process_activity_artifact_executions", "scope_key", nullable=False)
    op.create_index(
        "ix_process_activity_artifact_executions_scope_key",
        "process_activity_artifact_executions",
        ["scope_key"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_process_artifact_execution_scope",
        "process_activity_artifact_executions",
        ["company_id", "process_instance_id", "artifact_definition_id", "scope_key"],
    )
    op.create_table(
        "process_activity_artifact_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("process_instance_id", sa.Integer(), nullable=False),
        sa.Column("activity_execution_id", sa.Integer(), nullable=False),
        sa.Column("artifact_execution_id", sa.Integer(), nullable=False),
        sa.Column("phase_key", sa.String(length=80), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
        sa.ForeignKeyConstraint(["activity_execution_id"], ["process_instance_executions.id"]),
        sa.ForeignKeyConstraint(["artifact_execution_id"], ["process_activity_artifact_executions.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_process_artifact_interaction_company_execution", "process_activity_artifact_interactions", ["company_id", "artifact_execution_id", "created_at"], unique=False)
    op.create_index("ix_process_activity_artifact_interactions_company_id", "process_activity_artifact_interactions", ["company_id"], unique=False)
    op.create_index("ix_process_activity_artifact_interactions_process_instance_id", "process_activity_artifact_interactions", ["process_instance_id"], unique=False)
    op.create_index("ix_process_activity_artifact_interactions_activity_execution_id", "process_activity_artifact_interactions", ["activity_execution_id"], unique=False)
    op.create_index("ix_process_activity_artifact_interactions_artifact_execution_id", "process_activity_artifact_interactions", ["artifact_execution_id"], unique=False)
    op.create_index("ix_process_activity_artifact_interactions_phase_key", "process_activity_artifact_interactions", ["phase_key"], unique=False)
    op.create_index("ix_process_activity_artifact_interactions_actor_user_id", "process_activity_artifact_interactions", ["actor_user_id"], unique=False)


def downgrade():
    op.drop_table("process_activity_artifact_interactions")
    op.drop_constraint("uq_process_artifact_execution_scope", "process_activity_artifact_executions", type_="unique")
    op.drop_index("ix_process_activity_artifact_executions_scope_key", table_name="process_activity_artifact_executions")
    op.drop_column("process_activity_artifact_executions", "scope_key")
    op.drop_index("ix_process_activity_artifact_definitions_execution_scope", table_name="process_activity_artifact_definitions")
    op.drop_constraint("ck_process_artifact_definition_execution_scope", "process_activity_artifact_definitions", type_="check")
    op.drop_column("process_activity_artifact_definitions", "execution_scope")
