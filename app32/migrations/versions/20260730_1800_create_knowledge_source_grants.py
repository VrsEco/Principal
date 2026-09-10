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


def _assert_existing_table_contract(inspector: sa.Inspector) -> None:
    """Falha fechada se uma tabela homônima não suportar os grants tenant-safe."""

    required_columns = {
        "id", "knowledge_source_id", "company_id", "grant_scope", "user_id", "employee_id",
        "metadata_json", "created_at",
    }
    actual_columns = {column["name"] for column in inspector.get_columns("knowledge_source_grants")}
    actual_constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("knowledge_source_grants")
        if constraint.get("name")
    }
    missing_columns = sorted(required_columns - actual_columns)
    missing_constraints = sorted({"ck_knowledge_source_grants_scope_target"} - actual_constraints)
    if missing_columns or missing_constraints:
        raise RuntimeError(
            "knowledge_source_grants já existe, mas não atende ao contrato da revision "
            f"20260730_1800; colunas ausentes={missing_columns}, "
            f"constraints ausentes={missing_constraints}."
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("knowledge_source_grants"):
        _assert_existing_table_contract(inspector)

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
        if_not_exists=True,
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
            if_not_exists=True,
        )
    op.create_index(
        "uq_knowledge_source_grants_company",
        "knowledge_source_grants",
        ["knowledge_source_id"],
        unique=True,
        postgresql_where=sa.text("grant_scope = 'company'"),
        if_not_exists=True,
    )
    op.create_index(
        "uq_knowledge_source_grants_user",
        "knowledge_source_grants",
        ["knowledge_source_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("grant_scope = 'user'"),
        if_not_exists=True,
    )
    op.create_index(
        "uq_knowledge_source_grants_employee",
        "knowledge_source_grants",
        ["knowledge_source_id", "employee_id"],
        unique=True,
        postgresql_where=sa.text("grant_scope = 'employee'"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("knowledge_source_grants")
