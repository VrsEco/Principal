"""reorganize financial budget matrix execution

Revision ID: 20260327_1130
Revises: 20260322_0900
Create Date: 2026-03-27 11:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260327_1130"
down_revision = "20260322_0900"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    if _has_table("financial_budget_lines") and not _has_column("financial_budget_lines", "planned_amount"):
        op.add_column(
            "financial_budget_lines",
            sa.Column("planned_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        )
        op.execute(
            """
            UPDATE financial_budget_lines line
               SET planned_amount = COALESCE((
                    SELECT SUM(amount.budget_amount)
                      FROM financial_budget_amounts amount
                     WHERE amount.budget_line_id = line.id
                       AND amount.deleted_at IS NULL
               ), 0)
            """
        )

    if not _has_table("financial_budget_contracts"):
        op.create_table(
            "financial_budget_contracts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("budget_line_id", sa.Integer(), nullable=False),
            sa.Column("contract_code", sa.String(length=60), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("contract_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("counterparty_id", sa.Integer(), nullable=True),
            sa.Column("signed_at", sa.Date(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint("status IN ('draft', 'active', 'closed', 'cancelled')", name="ck_financial_budget_contracts_status"),
            sa.CheckConstraint("contract_amount >= 0", name="ck_financial_budget_contracts_amount_nonneg"),
            sa.ForeignKeyConstraint(["budget_line_id"], ["financial_budget_lines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["counterparty_id"], ["financial_counterparties.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "contract_code", name="uq_financial_budget_contracts_company_code"),
        )

    if not _has_table("financial_budget_documents"):
        op.create_table(
            "financial_budget_documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("budget_contract_id", sa.Integer(), nullable=False),
            sa.Column("document_code", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("document_type", sa.String(length=20), nullable=False, server_default="invoice"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="registered"),
            sa.Column("document_number", sa.String(length=80), nullable=True),
            sa.Column("document_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("issue_date", sa.Date(), nullable=True),
            sa.Column("competence_date", sa.Date(), nullable=True),
            sa.Column("counterparty_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint("status IN ('draft', 'registered', 'scheduled', 'partially_scheduled', 'fully_scheduled', 'cancelled')", name="ck_financial_budget_documents_status"),
            sa.CheckConstraint("document_type IN ('invoice', 'equivalent')", name="ck_financial_budget_documents_type"),
            sa.CheckConstraint("document_amount >= 0", name="ck_financial_budget_documents_amount_nonneg"),
            sa.ForeignKeyConstraint(["budget_contract_id"], ["financial_budget_contracts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["counterparty_id"], ["financial_counterparties.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "document_code", name="uq_financial_budget_documents_company_code"),
        )

    if _has_table("financial_schedules") and not _has_column("financial_schedules", "budget_document_id"):
        op.add_column("financial_schedules", sa.Column("budget_document_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_financial_schedules_budget_document_id",
            "financial_schedules",
            "financial_budget_documents",
            ["budget_document_id"],
            ["id"],
        )

    indexes = [
        ("idx_financial_budget_contracts_company_line", "financial_budget_contracts", ["company_id", "budget_line_id"]),
        ("idx_financial_budget_contracts_company_counterparty", "financial_budget_contracts", ["company_id", "counterparty_id"]),
        ("idx_financial_budget_documents_company_contract", "financial_budget_documents", ["company_id", "budget_contract_id"]),
        ("idx_financial_budget_documents_company_counterparty", "financial_budget_documents", ["company_id", "counterparty_id"]),
        ("idx_financial_schedules_company_budget_document", "financial_schedules", ["company_id", "budget_document_id"]),
    ]
    for index_name, table_name, columns in indexes:
        if _has_table(table_name) and not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_schedules_company_budget_document", "financial_schedules"),
        ("idx_financial_budget_documents_company_counterparty", "financial_budget_documents"),
        ("idx_financial_budget_documents_company_contract", "financial_budget_documents"),
        ("idx_financial_budget_contracts_company_counterparty", "financial_budget_contracts"),
        ("idx_financial_budget_contracts_company_line", "financial_budget_contracts"),
    ]:
        if inspector.has_table(table_name) and _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
            inspector = sa.inspect(bind)

    if inspector.has_table("financial_schedules") and _has_column("financial_schedules", "budget_document_id"):
        try:
            op.drop_constraint("fk_financial_schedules_budget_document_id", "financial_schedules", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("financial_schedules", "budget_document_id")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_budget_documents"):
        op.drop_table("financial_budget_documents")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_budget_contracts"):
        op.drop_table("financial_budget_contracts")
        inspector = sa.inspect(bind)

    if inspector.has_table("financial_budget_lines") and _has_column("financial_budget_lines", "planned_amount"):
        op.drop_column("financial_budget_lines", "planned_amount")
