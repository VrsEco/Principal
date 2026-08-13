"""Add composite index for paginated project Kanban queries.

Revision ID: 20260813_1200
Revises: 20260802_2100
Create Date: 2026-08-13
"""

from alembic import op


revision = "20260813_1200"
down_revision = "20260802_2100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_project_tasks_board_page",
        "project_tasks",
        ["project_id", "is_deleted", "stage", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_tasks_board_page", table_name="project_tasks")

