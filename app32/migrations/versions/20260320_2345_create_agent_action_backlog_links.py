"""create agent action backlog links

Revision ID: 20260320_2345
Revises: 20260320_2245
Create Date: 2026-03-20 23:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_2345"
down_revision = "20260320_2245"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("agent_action_backlog_links"):
        return

    op.create_table(
        "agent_action_backlog_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("agent_action_id", sa.Integer(), nullable=False),
        sa.Column("project_task_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.Column("backlog_project_code", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_action_id"], ["agent_actions.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["project_task_id"], ["project_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_action_id",
            name="uq_agent_action_backlog_links_agent_action_id",
        ),
        sa.UniqueConstraint(
            "project_task_id",
            name="uq_agent_action_backlog_links_project_task_id",
        ),
    )
    op.create_index(
        op.f("ix_agent_action_backlog_links_company_id"),
        "agent_action_backlog_links",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_action_backlog_links_agent_action_id"),
        "agent_action_backlog_links",
        ["agent_action_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_action_backlog_links_project_task_id"),
        "agent_action_backlog_links",
        ["project_task_id"],
        unique=False,
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("agent_action_backlog_links"):
        return

    op.drop_index(
        op.f("ix_agent_action_backlog_links_project_task_id"),
        table_name="agent_action_backlog_links",
    )
    op.drop_index(
        op.f("ix_agent_action_backlog_links_agent_action_id"),
        table_name="agent_action_backlog_links",
    )
    op.drop_index(
        op.f("ix_agent_action_backlog_links_company_id"),
        table_name="agent_action_backlog_links",
    )
    op.drop_table("agent_action_backlog_links")
