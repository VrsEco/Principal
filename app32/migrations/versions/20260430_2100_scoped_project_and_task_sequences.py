"""scoped_project_and_task_sequences

Revision ID: 20260430_2100
Revises: 20260427_2130
Create Date: 2026-04-30 21:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_2100"
down_revision = "20260427_2130"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _has_unique(inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {item["name"] for item in inspector.get_unique_constraints(table_name)}


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if _has_table(inspector, "projects") and not _has_column(inspector, "projects", "code_sequence"):
        op.add_column("projects", sa.Column("code_sequence", sa.Integer(), nullable=True))
        op.execute(
            """
            WITH ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY id) AS seq
                FROM projects
            )
            UPDATE projects p
            SET code_sequence = ranked.seq
            FROM ranked
            WHERE ranked.id = p.id
            """
        )
        op.alter_column("projects", "code_sequence", nullable=False)

    inspector = sa.inspect(conn)
    if _has_table(inspector, "projects") and not _has_unique(inspector, "projects", "uq_projects_company_code_sequence"):
        op.create_unique_constraint(
            "uq_projects_company_code_sequence",
            "projects",
            ["company_id", "code_sequence"],
        )

    inspector = sa.inspect(conn)
    if _has_table(inspector, "project_tasks") and not _has_column(inspector, "project_tasks", "code_sequence"):
        op.add_column("project_tasks", sa.Column("code_sequence", sa.Integer(), nullable=True))
        op.execute(
            """
            WITH ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id) AS seq
                FROM project_tasks
            )
            UPDATE project_tasks pt
            SET code_sequence = ranked.seq
            FROM ranked
            WHERE ranked.id = pt.id
            """
        )
        op.alter_column("project_tasks", "code_sequence", nullable=False)

    inspector = sa.inspect(conn)
    if _has_table(inspector, "project_tasks") and not _has_unique(inspector, "project_tasks", "uq_project_tasks_project_code_sequence"):
        op.create_unique_constraint(
            "uq_project_tasks_project_code_sequence",
            "project_tasks",
            ["project_id", "code_sequence"],
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if _has_table(inspector, "project_tasks"):
        if _has_unique(inspector, "project_tasks", "uq_project_tasks_project_code_sequence"):
            op.drop_constraint("uq_project_tasks_project_code_sequence", "project_tasks", type_="unique")
        if _has_column(inspector, "project_tasks", "code_sequence"):
            op.drop_column("project_tasks", "code_sequence")

    inspector = sa.inspect(conn)
    if _has_table(inspector, "projects"):
        if _has_unique(inspector, "projects", "uq_projects_company_code_sequence"):
            op.drop_constraint("uq_projects_company_code_sequence", "projects", type_="unique")
        if _has_column(inspector, "projects", "code_sequence"):
            op.drop_column("projects", "code_sequence")
