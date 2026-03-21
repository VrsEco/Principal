"""create financial import hub

Revision ID: 20260318_2330
Revises: 20260318_2200
Create Date: 2026-03-18 23:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260318_2330"
down_revision = "20260318_2200"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    if not _has_table("financial_import_batches"):
        op.create_table(
            "financial_import_batches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("batch_code", sa.String(length=50), nullable=False),
            sa.Column("source_type", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="uploaded"),
            sa.Column("file_name", sa.String(length=255), nullable=True),
            sa.Column("file_hash", sa.String(length=64), nullable=True),
            sa.Column("imported_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
            sa.Column("uploaded_by_employee_id", sa.Integer(), nullable=True),
            sa.Column("created_by_agent", sa.String(length=50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["uploaded_by_employee_id"], ["employees.id"]),
            sa.UniqueConstraint("company_id", "batch_code", name="uq_financial_import_batches_company_code"),
            sa.CheckConstraint("source_type IN ('csv', 'csc', 'xlsx', 'ofx', 'api', 'mcp')", name="ck_financial_import_batches_source_type"),
            sa.CheckConstraint("status IN ('uploaded', 'parsed', 'processed', 'processed_with_errors', 'cancelled')", name="ck_financial_import_batches_status"),
            sa.CheckConstraint("total_rows >= 0", name="ck_financial_import_batches_total_rows_nonneg"),
            sa.CheckConstraint("valid_rows >= 0", name="ck_financial_import_batches_valid_rows_nonneg"),
            sa.CheckConstraint("error_rows >= 0", name="ck_financial_import_batches_error_rows_nonneg"),
        )

    if not _has_table("financial_import_rows"):
        op.create_table(
            "financial_import_rows",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("import_batch_id", sa.Integer(), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="staged"),
            sa.Column("document_number", sa.String(length=80), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("occurred_on", sa.Date(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("movement_nature", sa.String(length=10), nullable=True),
            sa.Column("bank_reference", sa.String(length=120), nullable=True),
            sa.Column("counterparty_name", sa.String(length=255), nullable=True),
            sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("normalized_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("matched_entry_id", sa.Integer(), nullable=True),
            sa.Column("created_entry_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["import_batch_id"], ["financial_import_batches.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["matched_entry_id"], ["financial_entries.id"]),
            sa.ForeignKeyConstraint(["created_entry_id"], ["financial_entries.id"]),
            sa.CheckConstraint("processing_status IN ('staged', 'validated', 'rejected', 'imported')", name="ck_financial_import_rows_processing_status"),
        )

    indexes = [
        ("idx_financial_import_batches_company_status", "financial_import_batches", ["company_id", "status"]),
        ("idx_financial_import_batches_company_source", "financial_import_batches", ["company_id", "source_type"]),
        ("idx_financial_import_rows_batch_status", "financial_import_rows", ["import_batch_id", "processing_status"]),
        ("idx_financial_import_rows_company_created_entry", "financial_import_rows", ["company_id", "created_entry_id"]),
    ]
    for index_name, table_name, columns in indexes:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_import_rows_company_created_entry", "financial_import_rows"),
        ("idx_financial_import_rows_batch_status", "financial_import_rows"),
        ("idx_financial_import_batches_company_source", "financial_import_batches"),
        ("idx_financial_import_batches_company_status", "financial_import_batches"),
    ]:
        if inspector.has_table(table_name):
            indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            if index_name in indexes:
                op.drop_index(index_name, table_name=table_name)

    if inspector.has_table("financial_import_rows"):
        op.drop_table("financial_import_rows")
    if inspector.has_table("financial_import_batches"):
        op.drop_table("financial_import_batches")
