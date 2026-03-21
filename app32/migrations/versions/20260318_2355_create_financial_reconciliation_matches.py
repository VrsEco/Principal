"""create financial reconciliation matches

Revision ID: 20260318_2355
Revises: 20260318_2330
Create Date: 2026-03-18 23:55:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260318_2355"
down_revision = "20260318_2330"
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
    if not _has_table("financial_reconciliation_matches"):
        op.create_table(
            "financial_reconciliation_matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("import_batch_id", sa.Integer(), nullable=False),
            sa.Column("import_row_id", sa.Integer(), nullable=False),
            sa.Column("financial_entry_id", sa.Integer(), nullable=False),
            sa.Column("match_status", sa.String(length=20), nullable=False, server_default="suggested"),
            sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
            sa.Column("match_reason", sa.String(length=255), nullable=True),
            sa.Column("matched_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("matched_date", sa.Date(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["import_batch_id"], ["financial_import_batches.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["import_row_id"], ["financial_import_rows.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["financial_entry_id"], ["financial_entries.id"], ondelete="CASCADE"),
            sa.CheckConstraint("match_status IN ('suggested', 'confirmed', 'rejected')", name="ck_financial_reconciliation_matches_status"),
            sa.CheckConstraint("(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)", name="ck_financial_reconciliation_matches_confidence"),
        )

    indexes = [
        ("idx_financial_reconciliation_matches_row_status", "financial_reconciliation_matches", ["import_row_id", "match_status"]),
        ("idx_financial_reconciliation_matches_entry_status", "financial_reconciliation_matches", ["financial_entry_id", "match_status"]),
        ("idx_financial_reconciliation_matches_company_batch", "financial_reconciliation_matches", ["company_id", "import_batch_id"]),
    ]
    for index_name, table_name, columns in indexes:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_reconciliation_matches_company_batch", "financial_reconciliation_matches"),
        ("idx_financial_reconciliation_matches_entry_status", "financial_reconciliation_matches"),
        ("idx_financial_reconciliation_matches_row_status", "financial_reconciliation_matches"),
    ]:
        if inspector.has_table(table_name):
            indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            if index_name in indexes:
                op.drop_index(index_name, table_name=table_name)

    if inspector.has_table("financial_reconciliation_matches"):
        op.drop_table("financial_reconciliation_matches")
