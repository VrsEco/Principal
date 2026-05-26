"""create process portal publications

Revision ID: 20260520_2300
Revises: 20260520_1700
Create Date: 2026-05-20 23:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260520_2300"
down_revision = "20260520_1700"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "process_portal_publications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.Column("source_bpmn_diagram_id", sa.Integer(), nullable=True),
        sa.Column("publication_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("visibility_scope", sa.String(length=30), nullable=False, server_default="linked_process"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("published_by_user_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_bpmn_diagram_id"], ["process_bpmn_diagrams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_process_portal_publications_company_id", "process_portal_publications", ["company_id"])
    op.create_index("ix_process_portal_publications_process_id", "process_portal_publications", ["process_id"])
    op.create_index(
        "ix_process_portal_publications_source_bpmn_diagram_id",
        "process_portal_publications",
        ["source_bpmn_diagram_id"],
    )
    op.create_index(
        "uq_process_portal_publications_process_version",
        "process_portal_publications",
        ["company_id", "process_id", "publication_version"],
        unique=True,
    )

    op.create_table(
        "process_portal_publication_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("publication_id", sa.Integer(), nullable=False),
        sa.Column("grant_scope", sa.String(length=30), nullable=False, server_default="user"),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("process_routine_id", sa.Integer(), nullable=True),
        sa.Column("bpmn_element_id", sa.String(length=255), nullable=True),
        sa.Column("can_view", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.ForeignKeyConstraint(["process_routine_id"], ["process_routines.id"]),
        sa.ForeignKeyConstraint(["publication_id"], ["process_portal_publications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_process_portal_publication_grants_company_id",
        "process_portal_publication_grants",
        ["company_id"],
    )
    op.create_index(
        "ix_process_portal_publication_grants_publication_id",
        "process_portal_publication_grants",
        ["publication_id"],
    )
    op.create_index(
        "ix_process_portal_publication_grants_user_id",
        "process_portal_publication_grants",
        ["user_id"],
    )
    op.create_index(
        "ix_process_portal_publication_grants_employee_id",
        "process_portal_publication_grants",
        ["employee_id"],
    )
    op.create_index(
        "ix_process_portal_publication_grants_process_routine_id",
        "process_portal_publication_grants",
        ["process_routine_id"],
    )
    op.create_index(
        "ix_process_portal_publication_grants_bpmn_element_id",
        "process_portal_publication_grants",
        ["bpmn_element_id"],
    )


def downgrade():
    op.drop_index("ix_process_portal_publication_grants_bpmn_element_id", table_name="process_portal_publication_grants")
    op.drop_index("ix_process_portal_publication_grants_process_routine_id", table_name="process_portal_publication_grants")
    op.drop_index("ix_process_portal_publication_grants_employee_id", table_name="process_portal_publication_grants")
    op.drop_index("ix_process_portal_publication_grants_user_id", table_name="process_portal_publication_grants")
    op.drop_index("ix_process_portal_publication_grants_publication_id", table_name="process_portal_publication_grants")
    op.drop_index("ix_process_portal_publication_grants_company_id", table_name="process_portal_publication_grants")
    op.drop_table("process_portal_publication_grants")

    op.drop_index("uq_process_portal_publications_process_version", table_name="process_portal_publications")
    op.drop_index("ix_process_portal_publications_source_bpmn_diagram_id", table_name="process_portal_publications")
    op.drop_index("ix_process_portal_publications_process_id", table_name="process_portal_publications")
    op.drop_index("ix_process_portal_publications_company_id", table_name="process_portal_publications")
    op.drop_table("process_portal_publications")
