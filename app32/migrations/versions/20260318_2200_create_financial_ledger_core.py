"""create financial ledger core tables

Revision ID: 20260318_2200
Revises: 77ecdce92559
Create Date: 2026-03-18 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260318_2200"
down_revision = "77ecdce92559"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    if not _has_table("financial_entries"):
        op.create_table(
            "financial_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("entry_code", sa.String(length=50), nullable=False),
            sa.Column("entry_type", sa.String(length=30), nullable=False),
            sa.Column("movement_nature", sa.String(length=10), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
            sa.Column("origin_type", sa.String(length=30), nullable=False, server_default="manual"),
            sa.Column("description", sa.String(length=255), nullable=False),
            sa.Column("memo", sa.Text(), nullable=True),
            sa.Column("document_number", sa.String(length=80), nullable=True),
            sa.Column("external_reference", sa.String(length=120), nullable=True),
            sa.Column("origin_reference", sa.String(length=120), nullable=True),
            sa.Column("issue_date", sa.Date(), nullable=True),
            sa.Column("competence_date", sa.Date(), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("occurred_on", sa.Date(), nullable=True),
            sa.Column("original_amount", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="BRL"),
            sa.Column("bank_account_id", sa.Integer(), nullable=True),
            sa.Column("counterparty_id", sa.Integer(), nullable=True),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("process_instance_id", sa.Integer(), nullable=True),
            sa.Column("routine_id", sa.Integer(), nullable=True),
            sa.Column("review_status", sa.String(length=30), nullable=False, server_default="pending_review"),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_employee_id", sa.Integer(), nullable=True),
            sa.Column("created_by_agent", sa.String(length=50), nullable=True),
            sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint("original_amount >= 0", name="ck_financial_entries_original_amount_nonneg"),
            sa.CheckConstraint(
                "entry_type IN ('payable', 'receivable', 'bank_movement', 'transfer', 'adjustment', 'forecast')",
                name="ck_financial_entries_entry_type",
            ),
            sa.CheckConstraint(
                "movement_nature IN ('debit', 'credit')",
                name="ck_financial_entries_movement_nature",
            ),
            sa.CheckConstraint(
                "status IN ('draft', 'pending_review', 'scheduled', 'posted', 'partially_settled', 'settled', 'cancelled')",
                name="ck_financial_entries_status",
            ),
            sa.CheckConstraint(
                "origin_type IN ('manual', 'process', 'routine', 'sapiens', 'ofx', 'csv', 'xls', 'csc', 'api', 'mcp', 'migration')",
                name="ck_financial_entries_origin_type",
            ),
            sa.CheckConstraint(
                "review_status IN ('pending_review', 'suggested_by_ai', 'reviewed', 'approved', 'rejected')",
                name="ck_financial_entries_review_status",
            ),
            sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
            sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_employee_id"], ["employees.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
            sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "entry_code", name="uq_financial_entries_company_code"),
        )

    if not _has_table("financial_entry_allocations"):
        op.create_table(
            "financial_entry_allocations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("financial_entry_id", sa.Integer(), nullable=False),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("process_instance_id", sa.Integer(), nullable=True),
            sa.Column("routine_id", sa.Integer(), nullable=True),
            sa.Column("allocation_type", sa.String(length=20), nullable=False),
            sa.Column("percentage", sa.Numeric(precision=7, scale=4), nullable=True),
            sa.Column("allocated_amount", sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "allocation_type IN ('percentage', 'amount')",
                name="ck_financial_entry_allocations_type",
            ),
            sa.CheckConstraint(
                "(percentage IS NULL OR percentage >= 0) AND (allocated_amount IS NULL OR allocated_amount >= 0)",
                name="ck_financial_entry_allocations_nonneg",
            ),
            sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["financial_entry_id"], ["financial_entries.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
            sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("financial_settlements"):
        op.create_table(
            "financial_settlements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("financial_entry_id", sa.Integer(), nullable=False),
            sa.Column("settlement_code", sa.String(length=50), nullable=False),
            sa.Column("settlement_type", sa.String(length=30), nullable=False),
            sa.Column("settlement_status", sa.String(length=30), nullable=False, server_default="posted"),
            sa.Column("settlement_date", sa.Date(), nullable=False),
            sa.Column("bank_account_id", sa.Integer(), nullable=True),
            sa.Column("principal_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("interest_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("penalty_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("fee_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("other_adjustments_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"),
            sa.Column("net_amount", sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column("external_reference", sa.String(length=120), nullable=True),
            sa.Column("import_batch_id", sa.Integer(), nullable=True),
            sa.Column("reconciliation_status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_by_employee_id", sa.Integer(), nullable=True),
            sa.Column("created_by_agent", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "settlement_type IN ('manual', 'bank_import', 'api', 'mcp', 'automatic_process', 'automatic_rule', 'reversal')",
                name="ck_financial_settlements_type",
            ),
            sa.CheckConstraint(
                "settlement_status IN ('draft', 'posted', 'reversed', 'cancelled')",
                name="ck_financial_settlements_status",
            ),
            sa.CheckConstraint(
                "reconciliation_status IN ('pending', 'suggested', 'matched', 'reconciled', 'rejected')",
                name="ck_financial_settlements_reconciliation_status",
            ),
            sa.CheckConstraint(
                """
                principal_amount >= 0 AND interest_amount >= 0 AND penalty_amount >= 0
                AND discount_amount >= 0 AND fee_amount >= 0 AND other_adjustments_amount >= 0
                AND net_amount >= 0
                """,
                name="ck_financial_settlements_amounts_nonneg",
            ),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["created_by_employee_id"], ["employees.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["financial_entry_id"], ["financial_entries.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "settlement_code", name="uq_financial_settlements_company_code"),
        )

    indexes = [
        ("idx_financial_entries_company_status", "financial_entries", ["company_id", "status"]),
        ("idx_financial_entries_company_competence", "financial_entries", ["company_id", "competence_date"]),
        ("idx_financial_entries_company_due", "financial_entries", ["company_id", "due_date"]),
        ("idx_financial_entries_company_activity", "financial_entries", ["company_id", "activity_id"]),
        ("idx_financial_entries_company_instance", "financial_entries", ["company_id", "process_instance_id"]),
        ("idx_financial_allocations_company_entry", "financial_entry_allocations", ["company_id", "financial_entry_id"]),
        ("idx_financial_allocations_company_activity", "financial_entry_allocations", ["company_id", "activity_id"]),
        ("idx_financial_allocations_company_instance", "financial_entry_allocations", ["company_id", "process_instance_id"]),
        ("idx_financial_settlements_company_entry", "financial_settlements", ["company_id", "financial_entry_id"]),
        ("idx_financial_settlements_company_date", "financial_settlements", ["company_id", "settlement_date"]),
        ("idx_financial_settlements_company_recon", "financial_settlements", ["company_id", "reconciliation_status"]),
    ]

    for index_name, table_name, columns in indexes:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_settlements_company_recon", "financial_settlements"),
        ("idx_financial_settlements_company_date", "financial_settlements"),
        ("idx_financial_settlements_company_entry", "financial_settlements"),
        ("idx_financial_allocations_company_instance", "financial_entry_allocations"),
        ("idx_financial_allocations_company_activity", "financial_entry_allocations"),
        ("idx_financial_allocations_company_entry", "financial_entry_allocations"),
        ("idx_financial_entries_company_instance", "financial_entries"),
        ("idx_financial_entries_company_activity", "financial_entries"),
        ("idx_financial_entries_company_due", "financial_entries"),
        ("idx_financial_entries_company_competence", "financial_entries"),
        ("idx_financial_entries_company_status", "financial_entries"),
    ]:
        if inspector.has_table(table_name) and _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
            inspector = sa.inspect(bind)

    if inspector.has_table("financial_settlements"):
        op.drop_table("financial_settlements")
        inspector = sa.inspect(bind)
    if inspector.has_table("financial_entry_allocations"):
        op.drop_table("financial_entry_allocations")
        inspector = sa.inspect(bind)
    if inspector.has_table("financial_entries"):
        op.drop_table("financial_entries")
