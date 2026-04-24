"""reconcile financial automation center schema to current v2 contract

Revision ID: 20260423_2200
Revises: 20260420_1500
Create Date: 2026-04-23 22:00:00
"""

from alembic import op


revision = "20260423_2200"
down_revision = "20260420_1500"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.financial_automation_batches (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            origin_type VARCHAR(50) NOT NULL,
            source_label VARCHAR(255),
            created_by_user_id INTEGER REFERENCES public.users(id),
            status_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );

        CREATE TABLE IF NOT EXISTS public.financial_automation_documents (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            batch_id INTEGER NOT NULL REFERENCES public.financial_automation_batches(id),
            file_name VARCHAR(255) NOT NULL,
            stored_relative_path VARCHAR(500),
            original_relative_path VARCHAR(500),
            optimized_relative_path VARCHAR(500),
            preview_relative_path VARCHAR(500),
            mime_type VARCHAR(120),
            file_size INTEGER,
            file_size_original INTEGER,
            file_size_optimized INTEGER,
            sha256 VARCHAR(64),
            document_family VARCHAR(30),
            document_type VARCHAR(50),
            source_kind VARCHAR(30),
            parser_status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
            parser_version VARCHAR(30),
            document_group_key VARCHAR(255),
            confidence_score NUMERIC(5, 4),
            extracted_text TEXT,
            preview_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            structured_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );

        CREATE TABLE IF NOT EXISTS public.financial_automation_records (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            batch_id INTEGER NOT NULL REFERENCES public.financial_automation_batches(id),
            source_document_id INTEGER REFERENCES public.financial_automation_documents(id),
            status VARCHAR(20) NOT NULL DEFAULT 'imported',
            entry_direction VARCHAR(20) NOT NULL,
            settlement_state VARCHAR(20) NOT NULL DEFAULT 'open',
            description VARCHAR(255),
            counterparty_id INTEGER REFERENCES public.financial_counterparties(id),
            bank_account_id INTEGER REFERENCES public.financial_bank_accounts(id),
            chart_account_id INTEGER REFERENCES public.financial_chart_accounts(id),
            cost_center_id INTEGER REFERENCES public.financial_cost_centers(id),
            domain_type VARCHAR(20),
            domain_source_id INTEGER,
            document_group_key VARCHAR(255),
            document_type VARCHAR(50),
            document_key VARCHAR(64),
            external_document_number VARCHAR(120),
            issuer_name VARCHAR(255),
            issuer_document VARCHAR(32),
            recipient_name VARCHAR(255),
            recipient_document VARCHAR(32),
            issue_date DATE,
            amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            competence_date DATE,
            due_date DATE,
            confidence_score NUMERIC(5, 4),
            validation_notes TEXT,
            extracted_fields_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            review_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            normalized_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            generated_financial_entry_id INTEGER REFERENCES public.financial_entries(id),
            generated_financial_schedule_id INTEGER REFERENCES public.financial_schedules(id),
            validated_by_user_id INTEGER REFERENCES public.users(id),
            validated_at TIMESTAMP WITHOUT TIME ZONE,
            generated_by_user_id INTEGER REFERENCES public.users(id),
            generated_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );

        CREATE TABLE IF NOT EXISTS public.financial_automation_history (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            record_id INTEGER NOT NULL REFERENCES public.financial_automation_records(id),
            action_type VARCHAR(50) NOT NULL,
            performed_by_user_id INTEGER REFERENCES public.users(id),
            payload_before_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            payload_after_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );

        ALTER TABLE public.financial_automation_documents
            ADD COLUMN IF NOT EXISTS original_relative_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS optimized_relative_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS preview_relative_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS file_size_original INTEGER,
            ADD COLUMN IF NOT EXISTS file_size_optimized INTEGER,
            ADD COLUMN IF NOT EXISTS document_family VARCHAR(30),
            ADD COLUMN IF NOT EXISTS document_type VARCHAR(50),
            ADD COLUMN IF NOT EXISTS source_kind VARCHAR(30),
            ADD COLUMN IF NOT EXISTS parser_status VARCHAR(30),
            ADD COLUMN IF NOT EXISTS parser_version VARCHAR(30),
            ADD COLUMN IF NOT EXISTS document_group_key VARCHAR(255),
            ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(5, 4),
            ADD COLUMN IF NOT EXISTS structured_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb;

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

        UPDATE public.financial_automation_documents
           SET original_relative_path = COALESCE(original_relative_path, stored_relative_path),
               file_size_original = COALESCE(file_size_original, file_size),
               parser_status = COALESCE(NULLIF(parser_status, ''), 'uploaded'),
               structured_payload_json = COALESCE(structured_payload_json, '{}'::jsonb)
         WHERE TRUE;

        UPDATE public.financial_automation_records
           SET extracted_fields_json = COALESCE(extracted_fields_json, '{}'::jsonb),
               review_flags_json = COALESCE(review_flags_json, '[]'::jsonb)
         WHERE TRUE;

        CREATE INDEX IF NOT EXISTS ix_financial_automation_batches_company_id
            ON public.financial_automation_batches (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_batches_company_origin_created
            ON public.financial_automation_batches (company_id, origin_type, created_at);

        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_id
            ON public.financial_automation_documents (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_batch
            ON public.financial_automation_documents (company_id, batch_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_group
            ON public.financial_automation_documents (company_id, document_group_key);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_type
            ON public.financial_automation_documents (company_id, document_type);

        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_id
            ON public.financial_automation_records (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_status
            ON public.financial_automation_records (company_id, status);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_batch
            ON public.financial_automation_records (company_id, batch_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_generated_entry
            ON public.financial_automation_records (generated_financial_entry_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_generated_schedule
            ON public.financial_automation_records (generated_financial_schedule_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_group
            ON public.financial_automation_records (company_id, document_group_key);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_company_document_key
            ON public.financial_automation_records (company_id, document_key);

        CREATE INDEX IF NOT EXISTS ix_financial_automation_history_company_id
            ON public.financial_automation_history (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_history_company_record
            ON public.financial_automation_history (company_id, record_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_financial_automation_history_company_record;
        DROP INDEX IF EXISTS public.ix_financial_automation_history_company_id;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_document_key;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_group;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_generated_schedule;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_generated_entry;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_batch;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_status;
        DROP INDEX IF EXISTS public.ix_financial_automation_records_company_id;
        DROP INDEX IF EXISTS public.ix_financial_automation_documents_company_type;
        DROP INDEX IF EXISTS public.ix_financial_automation_documents_company_group;
        DROP INDEX IF EXISTS public.ix_financial_automation_documents_company_batch;
        DROP INDEX IF EXISTS public.ix_financial_automation_documents_company_id;
        DROP INDEX IF EXISTS public.ix_financial_automation_batches_company_origin_created;
        DROP INDEX IF EXISTS public.ix_financial_automation_batches_company_id;
        """
    )
