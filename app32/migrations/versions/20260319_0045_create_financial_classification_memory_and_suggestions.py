"""create financial classification memory and suggestions

Revision ID: 20260319_0045
Revises: 20260319_0015
Create Date: 2026-03-19 00:45:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260319_0045"
down_revision = "20260319_0015"
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
    if not _has_table("financial_classification_memories"):
        op.create_table(
            "financial_classification_memories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("supplier_name", sa.String(length=255), nullable=True),
            sa.Column("supplier_document", sa.String(length=50), nullable=True),
            sa.Column("description_pattern", sa.String(length=255), nullable=True),
            sa.Column("product_hint", sa.String(length=255), nullable=True),
            sa.Column("amount_range_min", sa.Numeric(14, 2), nullable=True),
            sa.Column("amount_range_max", sa.Numeric(14, 2), nullable=True),
            sa.Column("entry_type", sa.String(length=30), nullable=True),
            sa.Column("movement_nature", sa.String(length=10), nullable=True),
            sa.Column("chart_account_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column("activity_id", sa.Integer(), nullable=True),
            sa.Column("process_instance_id", sa.Integer(), nullable=True),
            sa.Column("routine_id", sa.Integer(), nullable=True),
            sa.Column("counterparty_hint", sa.String(length=255), nullable=True),
            sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
            sa.Column("times_confirmed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_confirmed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("last_confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("source", sa.String(length=30), nullable=False, server_default="user_confirmed"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["activity_id"], ["process_routines.id"]),
            sa.ForeignKeyConstraint(["process_instance_id"], ["process_instances.id"]),
            sa.ForeignKeyConstraint(["routine_id"], ["routines.id"]),
            sa.ForeignKeyConstraint(["last_confirmed_by_user_id"], ["users.id"]),
            sa.CheckConstraint("source IN ('user_confirmed', 'ai_suggested', 'imported_memory')", name="ck_financial_classification_memories_source"),
            sa.CheckConstraint("(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)", name="ck_financial_classification_memories_confidence"),
            sa.CheckConstraint("times_confirmed >= 0", name="ck_financial_classification_memories_times_confirmed_nonneg"),
        )

    if not _has_table("financial_classification_suggestions"):
        op.create_table(
            "financial_classification_suggestions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("import_batch_id", sa.Integer(), nullable=False),
            sa.Column("import_row_id", sa.Integer(), nullable=False),
            sa.Column("rank_position", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("source_layer", sa.String(length=20), nullable=False, server_default="memory"),
            sa.Column("score", sa.Numeric(5, 4), nullable=True),
            sa.Column("reason", sa.String(length=255), nullable=True),
            sa.Column("suggested_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="suggested"),
            sa.Column("confirmed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
            sa.ForeignKeyConstraint(["import_batch_id"], ["financial_import_batches.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["import_row_id"], ["financial_import_rows.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"]),
            sa.CheckConstraint("source_layer IN ('rule', 'memory', 'ai')", name="ck_financial_classification_suggestions_source_layer"),
            sa.CheckConstraint("status IN ('suggested', 'confirmed', 'rejected', 'applied')", name="ck_financial_classification_suggestions_status"),
            sa.CheckConstraint("(score IS NULL) OR (score >= 0 AND score <= 1)", name="ck_financial_classification_suggestions_score"),
        )

    indexes = [
        ("idx_financial_classification_memories_company_active", "financial_classification_memories", ["company_id", "is_active"]),
        ("idx_financial_classification_memories_company_supplier", "financial_classification_memories", ["company_id", "supplier_name"]),
        ("idx_financial_classification_suggestions_batch_row", "financial_classification_suggestions", ["import_batch_id", "import_row_id"]),
        ("idx_financial_classification_suggestions_company_status", "financial_classification_suggestions", ["company_id", "status"]),
    ]
    for index_name, table_name, columns in indexes:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for index_name, table_name in [
        ("idx_financial_classification_suggestions_company_status", "financial_classification_suggestions"),
        ("idx_financial_classification_suggestions_batch_row", "financial_classification_suggestions"),
        ("idx_financial_classification_memories_company_supplier", "financial_classification_memories"),
        ("idx_financial_classification_memories_company_active", "financial_classification_memories"),
    ]:
        if inspector.has_table(table_name):
            indexes = {index["name"] for index in inspector.get_indexes(table_name)}
            if index_name in indexes:
                op.drop_index(index_name, table_name=table_name)

    if inspector.has_table("financial_classification_suggestions"):
        op.drop_table("financial_classification_suggestions")
    if inspector.has_table("financial_classification_memories"):
        op.drop_table("financial_classification_memories")
