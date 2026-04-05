"""create project task due date change requests

Revision ID: 20260405_1200
Revises: 20260403_2010
Create Date: 2026-04-05 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_1200"
down_revision = "20260403_2010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "company_performance_settings",
        sa.Column(
            "postpone_penalty_points",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="-1",
        ),
    )
    op.add_column(
        "company_performance_settings",
        sa.Column(
            "allow_postpone_after_due_date",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "project_task_due_date_change_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column(
            "request_type", sa.String(length=20), nullable=False, server_default="postpone"
        ),
        sa.Column("old_due_date", sa.Date(), nullable=True),
        sa.Column("requested_due_date", sa.Date(), nullable=True),
        sa.Column("approved_due_date", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_name", sa.String(length=200), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_name", sa.String(length=200), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column(
            "was_after_due_date_when_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "penalty_points",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["project_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_project_task_due_date_change_requests_company_status",
        "project_task_due_date_change_requests",
        ["company_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_project_task_due_date_change_requests_company_project_task",
        "project_task_due_date_change_requests",
        ["company_id", "project_id", "task_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_task_due_date_change_requests_task_requested_at",
        "project_task_due_date_change_requests",
        ["task_id", "requested_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_project_task_due_date_change_requests_task_requested_at",
        table_name="project_task_due_date_change_requests",
    )
    op.drop_index(
        "ix_project_task_due_date_change_requests_company_project_task",
        table_name="project_task_due_date_change_requests",
    )
    op.drop_index(
        "ix_project_task_due_date_change_requests_company_status",
        table_name="project_task_due_date_change_requests",
    )
    op.drop_table("project_task_due_date_change_requests")

    op.drop_column("company_performance_settings", "allow_postpone_after_due_date")
    op.drop_column("company_performance_settings", "postpone_penalty_points")
