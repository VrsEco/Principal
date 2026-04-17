"""expand financial automation documents and records for documental ingestion v2

Revision ID: 20260417_1830
Revises: 20260417_1400
Create Date: 2026-04-17 18:30:00
"""

from alembic import op


revision = "20260417_1830"
down_revision = "20260417_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.financial_automation_documents
            ADD COLUMN IF NOT EXISTS original_relative_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS optimized_relative_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS preview_relative_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS file_size_original INTEGER,
            ADD COLUMN IF NOT EXISTS file_size_optimized INTEGER,
            ADD COLUMN IF NOT EXISTS document_family VARCHAR(30),
            ADD COLUMN IF NOT EXISTS document_type VARCHAR(50),
            ADD COLUMN IF NOT EXISTS source_kind VARCHAR(30),
            ADD COLUMN IF NOT EXISTS parser_status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
            ADD COLUMN IF NOT EXISTS parser_version VARCHAR(30),
            ADD COLUMN IF NOT EXISTS document_group_key VARCHAR(255),
            ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(5, 4),
            ADD COLUMN IF NOT EXISTS structured_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb;

        UPDATE public.financial_automation_documents
           SET original_relative_path = COALESCE(original_relative_path, stored_relative_path),
               file_size_original = COALESCE(file_size_original, file_size),
               parser_status = COALESCE(parser_status, 'uploaded')
         WHERE TRUE;

        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_group
            ON public.financial_automation_documents (company_id, document_group_key);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_type
            ON public.financial_automation_documents (company_id, document_type);

        ALTER TABLE public.financial_automation_records
            ADD COLUMN IF NOT EXISTS document_group_key VARCHAR(255),
            ADD COLUMN IF NOT EXISTS document_type VARCHAR(50),
            ADD COLUMN IF NOT EXISTS document_key VARCHAR(64),
            ADD COLUMN IF NOT EXISTS external_document_number VARCHAR(120),
            ADD COLUMN IF NOT EXISTS issuer_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS issuer_document VARCHAR(32),
            ADD COLUMN IF NOT EXISTS recipient_name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS recipient_document VARCHAR(32),
            ADD COLUMN IF NOT EXISTS issue_date DATE,
            ADD COLUMN IF NOT EXISTS extracted_fields_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS review_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb;

        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_group
            ON public.financial_automation_records (company_id, document_group_key);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_document_key
            ON public.financial_automation_records (company_id, document_key);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_document_key;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_group;
        ALTER TABLE public.financial_automation_records
            DROP COLUMN IF EXISTS review_flags_json,
            DROP COLUMN IF EXISTS extracted_fields_json,
            DROP COLUMN IF EXISTS issue_date,
            DROP COLUMN IF EXISTS recipient_document,
            DROP COLUMN IF EXISTS recipient_name,
            DROP COLUMN IF EXISTS issuer_document,
            DROP COLUMN IF EXISTS issuer_name,
            DROP COLUMN IF EXISTS external_document_number,
            DROP COLUMN IF EXISTS document_key,
            DROP COLUMN IF EXISTS document_type,
            DROP COLUMN IF EXISTS document_group_key;

        DROP INDEX IF EXISTS public.ix_financial_automation_documents_company_type;
        DROP INDEX IF EXISTS public.ix_financial_automation_documents_company_group;
        ALTER TABLE public.financial_automation_documents
            DROP COLUMN IF EXISTS structured_payload_json,
            DROP COLUMN IF EXISTS confidence_score,
            DROP COLUMN IF EXISTS document_group_key,
            DROP COLUMN IF EXISTS parser_version,
            DROP COLUMN IF EXISTS parser_status,
            DROP COLUMN IF EXISTS source_kind,
            DROP COLUMN IF EXISTS document_type,
            DROP COLUMN IF EXISTS document_family,
            DROP COLUMN IF EXISTS file_size_optimized,
            DROP COLUMN IF EXISTS file_size_original,
            DROP COLUMN IF EXISTS preview_relative_path,
            DROP COLUMN IF EXISTS optimized_relative_path,
            DROP COLUMN IF EXISTS original_relative_path;
        """
    )
