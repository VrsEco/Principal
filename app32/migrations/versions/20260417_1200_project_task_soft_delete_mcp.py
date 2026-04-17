"""add soft delete fields to project tasks for secure MCP mutations

Revision ID: 20260417_1200
Revises: 20260403_1910
Create Date: 2026-04-17 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_1200"
down_revision = "20260403_1910"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project_tasks",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("project_tasks", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("project_tasks", sa.Column("deleted_by_user_id", sa.Integer(), nullable=True))
    op.add_column("project_tasks", sa.Column("delete_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_project_tasks_deleted_by_user_id",
        "project_tasks",
        "users",
        ["deleted_by_user_id"],
        ["id"],
    )
    op.create_index(
        "ix_project_tasks_project_deleted",
        "project_tasks",
        ["project_id", "is_deleted"],
        unique=False,
    )
    op.alter_column("project_tasks", "is_deleted", server_default=None)


def downgrade():
    op.drop_index("ix_project_tasks_project_deleted", table_name="project_tasks")
    op.drop_constraint("fk_project_tasks_deleted_by_user_id", "project_tasks", type_="foreignkey")
    op.drop_column("project_tasks", "delete_reason")
    op.drop_column("project_tasks", "deleted_by_user_id")
    op.drop_column("project_tasks", "deleted_at")
    op.drop_column("project_tasks", "is_deleted")

