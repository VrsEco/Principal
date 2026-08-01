"""create process execution assignments

Revision ID: 20260801_1530
Revises: 20260801_1500
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260801_1530"
down_revision = "20260801_1500"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "process_execution_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "activity_execution_id",
            sa.Integer(),
            sa.ForeignKey("process_instance_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assignee_type", sa.String(length=20), nullable=False, server_default="employee"),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_key", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="assigned"),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="instance_fallback"),
        sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "assignee_type IN ('employee', 'team', 'role')",
            name="ck_process_execution_assignment_type",
        ),
        sa.CheckConstraint(
            "status IN ('assigned', 'claimed', 'completed', 'cancelled')",
            name="ck_process_execution_assignment_status",
        ),
        sa.CheckConstraint(
            "(assignee_type = 'employee' AND employee_id IS NOT NULL AND team_id IS NULL AND role_key IS NULL) OR "
            "(assignee_type = 'team' AND employee_id IS NULL AND team_id IS NOT NULL AND role_key IS NULL) OR "
            "(assignee_type = 'role' AND employee_id IS NULL AND team_id IS NULL AND role_key IS NOT NULL)",
            name="ck_process_execution_assignment_target",
        ),
    )
    for column in ("company_id", "activity_execution_id", "employee_id", "team_id", "role_key", "status"):
        op.create_index(f"ix_process_execution_assignments_{column}", "process_execution_assignments", [column])
    op.create_index(
        "ix_process_execution_assignment_company_activity_status",
        "process_execution_assignments",
        ["company_id", "activity_execution_id", "status"],
    )
    op.create_index(
        "ix_process_execution_assignment_company_employee_status",
        "process_execution_assignments",
        ["company_id", "employee_id", "status"],
    )
    op.create_index(
        "uq_process_execution_assignment_active",
        "process_execution_assignments",
        ["company_id", "activity_execution_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('assigned', 'claimed')"),
    )


def downgrade():
    op.drop_table("process_execution_assignments")
