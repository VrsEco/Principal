"""create financial ingestion records

Revision ID: 20260320_1200
Revises: 20260320_1100
Create Date: 2026-03-20 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260320_1200"
down_revision = "20260320_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_ingestion_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("origin_type", sa.String(length=30), nullable=False),
        sa.Column("origin_reference", sa.String(length=120), nullable=True),
        sa.Column("external_system", sa.String(length=80), nullable=True),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("source_mime_type", sa.String(length=120), nullable=True),
        sa.Column("source_channel", sa.String(length=50), nullable=True),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column("related_schedule_id", sa.Integer(), nullable=True),
        sa.Column("related_entry_id", sa.Integer(), nullable=True),
        sa.Column("completion_status", sa.String(length=30), nullable=False, server_default="received"),
        sa.Column("review_status", sa.String(length=30), nullable=False, server_default="pending_review"),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("confidence_level", sa.String(length=10), nullable=True),
        sa.Column("raw_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalized_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("llm_response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["import_batch_id"], ["financial_import_batches.id"]),
        sa.ForeignKeyConstraint(["related_schedule_id"], ["financial_schedules.id"]),
        sa.ForeignKeyConstraint(["related_entry_id"], ["financial_entries.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "origin_type IN ('manual', 'import_csv', 'import_xlsx', 'import_ofx', 'import_csc', 'api', 'mcp', 'sapiens_image', 'sapiens_document', 'bank_reconciliation', 'integration_erp')",
            name="ck_financial_ingestion_records_origin_type",
        ),
        sa.CheckConstraint(
            "completion_status IN ('received', 'parsed', 'normalized', 'draft', 'partial', 'classified_partial', 'classified_complete', 'review_required', 'approved', 'reconciled', 'settled', 'closed', 'rejected')",
            name="ck_financial_ingestion_records_completion_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('not_required', 'pending_review', 'reviewed', 'rejected')",
            name="ck_financial_ingestion_records_review_status",
        ),
        sa.CheckConstraint(
            "(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_financial_ingestion_records_confidence_score",
        ),
        sa.CheckConstraint(
            "(confidence_level IS NULL) OR (confidence_level IN ('high', 'medium', 'low'))",
            name="ck_financial_ingestion_records_confidence_level",
        ),
    )
    op.create_index(op.f("ix_financial_ingestion_records_company_id"), "financial_ingestion_records", ["company_id"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_origin_type"), "financial_ingestion_records", ["origin_type"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_origin_reference"), "financial_ingestion_records", ["origin_reference"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_external_system"), "financial_ingestion_records", ["external_system"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_source_channel"), "financial_ingestion_records", ["source_channel"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_import_batch_id"), "financial_ingestion_records", ["import_batch_id"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_related_schedule_id"), "financial_ingestion_records", ["related_schedule_id"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_related_entry_id"), "financial_ingestion_records", ["related_entry_id"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_completion_status"), "financial_ingestion_records", ["completion_status"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_review_status"), "financial_ingestion_records", ["review_status"], unique=False)
    op.create_index(op.f("ix_financial_ingestion_records_confidence_level"), "financial_ingestion_records", ["confidence_level"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_financial_ingestion_records_confidence_level"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_review_status"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_completion_status"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_related_entry_id"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_related_schedule_id"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_import_batch_id"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_source_channel"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_external_system"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_origin_reference"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_origin_type"), table_name="financial_ingestion_records")
    op.drop_index(op.f("ix_financial_ingestion_records_company_id"), table_name="financial_ingestion_records")
    op.drop_table("financial_ingestion_records")
