"""Create fail-closed grants for tenant-owned knowledge sources.

Revision ID: 20260730_1800
Revises: 20260730_1700
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_1800"
down_revision = "20260730_1700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_source_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "knowledge_source_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("grant_scope", sa.String(length=20), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(grant_scope = 'company' AND user_id IS NULL AND employee_id IS NULL) OR "
            "(grant_scope = 'user' AND user_id IS NOT NULL AND employee_id IS NULL) OR "
            "(grant_scope = 'employee' AND employee_id IS NOT NULL AND user_id IS NULL)",
            name="ck_knowledge_source_grants_scope_target",
        ),
    )
    for column in (
        "knowledge_source_id",
        "company_id",
        "grant_scope",
        "user_id",
        "employee_id",
    ):
        op.create_index(
            f"ix_knowledge_source_grants_{column}",
            "knowledge_source_grants",
            [column],
        )
    op.create_index(
        "uq_knowledge_source_grants_company",
        "knowledge_source_grants",
        ["knowledge_source_id"],
        unique=True,
        postgresql_where=sa.text("grant_scope = 'company'"),
    )
    op.create_index(
        "uq_knowledge_source_grants_user",
        "knowledge_source_grants",
        ["knowledge_source_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("grant_scope = 'user'"),
    )
    op.create_index(
        "uq_knowledge_source_grants_employee",
        "knowledge_source_grants",
        ["knowledge_source_id", "employee_id"],
        unique=True,
        postgresql_where=sa.text("grant_scope = 'employee'"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_source_grants")
