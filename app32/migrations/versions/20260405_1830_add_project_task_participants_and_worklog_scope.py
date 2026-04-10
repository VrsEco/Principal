"""add project task participants scope and work log tenant context

Revision ID: 20260405_1830
Revises: 20260405_1200
Create Date: 2026-04-05 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_1830"
down_revision = "20260405_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project_activity_collaborators",
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_activity_collaborators",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_activity_collaborators",
        sa.Column(
            "joined_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "project_activity_collaborators",
        sa.Column("removed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "project_activity_collaborators",
        sa.Column("created_by_employee_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_activity_collaborators",
        sa.Column("updated_by_employee_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_project_activity_collaborators_company_id",
        "project_activity_collaborators",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_project_activity_collaborators_project_id",
        "project_activity_collaborators",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_project_activity_collaborators_created_by_employee_id",
        "project_activity_collaborators",
        "employees",
        ["created_by_employee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_project_activity_collaborators_updated_by_employee_id",
        "project_activity_collaborators",
        "employees",
        ["updated_by_employee_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE project_activity_collaborators pac
           SET project_id = pt.project_id,
               company_id = p.company_id,
               joined_at = COALESCE(pac.created_at, now())
          FROM project_tasks pt
          JOIN projects p ON p.id = pt.project_id
         WHERE pt.id = pac.activity_id
        """
    )

    op.create_index(
        "ix_project_activity_collaborators_company_project",
        "project_activity_collaborators",
        ["company_id", "project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_activity_collaborators_company_activity",
        "project_activity_collaborators",
        ["company_id", "activity_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_activity_collaborators_company_employee",
        "project_activity_collaborators",
        ["company_id", "employee_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_project_activity_collab_active
            ON project_activity_collaborators (company_id, activity_id, employee_id)
         WHERE is_deleted = FALSE
        """
    )

    op.add_column(
        "activity_work_logs",
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "activity_work_logs",
        sa.Column("project_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "activity_work_logs",
        sa.Column("created_by_employee_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "activity_work_logs",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "activity_work_logs",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_foreign_key(
        "fk_activity_work_logs_company_id",
        "activity_work_logs",
        "companies",
        ["company_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_activity_work_logs_project_id",
        "activity_work_logs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_activity_work_logs_created_by_employee_id",
        "activity_work_logs",
        "employees",
        ["created_by_employee_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE activity_work_logs awl
           SET project_id = pt.project_id,
               company_id = p.company_id
          FROM project_tasks pt
          JOIN projects p ON p.id = pt.project_id
         WHERE awl.activity_type = 'project'
           AND pt.id = awl.activity_id
        """
    )
    op.execute(
        """
        UPDATE activity_work_logs awl
           SET company_id = pi.company_id
          FROM process_instances pi
         WHERE awl.activity_type = 'process_instance'
           AND pi.id = awl.activity_id
        """
    )

    op.create_index(
        "ix_activity_work_logs_company_activity",
        "activity_work_logs",
        ["company_id", "activity_type", "activity_id"],
        unique=False,
    )
    op.create_index(
        "ix_activity_work_logs_company_employee_work_date",
        "activity_work_logs",
        ["company_id", "employee_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_activity_work_logs_company_project",
        "activity_work_logs",
        ["company_id", "project_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_activity_work_logs_company_project", table_name="activity_work_logs")
    op.drop_index(
        "ix_activity_work_logs_company_employee_work_date",
        table_name="activity_work_logs",
    )
    op.drop_index("ix_activity_work_logs_company_activity", table_name="activity_work_logs")
    op.drop_constraint(
        "fk_activity_work_logs_created_by_employee_id",
        "activity_work_logs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_activity_work_logs_project_id",
        "activity_work_logs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_activity_work_logs_company_id",
        "activity_work_logs",
        type_="foreignkey",
    )
    op.drop_column("activity_work_logs", "is_deleted")
    op.drop_column("activity_work_logs", "updated_at")
    op.drop_column("activity_work_logs", "created_by_employee_id")
    op.drop_column("activity_work_logs", "project_id")
    op.drop_column("activity_work_logs", "company_id")

    op.execute("DROP INDEX IF EXISTS uq_project_activity_collab_active")
    op.drop_index(
        "ix_project_activity_collaborators_company_employee",
        table_name="project_activity_collaborators",
    )
    op.drop_index(
        "ix_project_activity_collaborators_company_activity",
        table_name="project_activity_collaborators",
    )
    op.drop_index(
        "ix_project_activity_collaborators_company_project",
        table_name="project_activity_collaborators",
    )
    op.drop_constraint(
        "fk_project_activity_collaborators_updated_by_employee_id",
        "project_activity_collaborators",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_project_activity_collaborators_created_by_employee_id",
        "project_activity_collaborators",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_project_activity_collaborators_project_id",
        "project_activity_collaborators",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_project_activity_collaborators_company_id",
        "project_activity_collaborators",
        type_="foreignkey",
    )
    op.drop_column("project_activity_collaborators", "updated_by_employee_id")
    op.drop_column("project_activity_collaborators", "created_by_employee_id")
    op.drop_column("project_activity_collaborators", "removed_at")
    op.drop_column("project_activity_collaborators", "joined_at")
    op.drop_column("project_activity_collaborators", "project_id")
    op.drop_column("project_activity_collaborators", "company_id")
