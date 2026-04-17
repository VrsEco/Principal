"""create financial automation center tables

Revision ID: 20260417_1400
Revises: 20260403_1910
Create Date: 2026-04-17 14:00:00
"""

from alembic import op


revision = "20260417_1400"
down_revision = "20260403_1910"
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

        CREATE INDEX IF NOT EXISTS ix_financial_automation_batches_company_id
            ON public.financial_automation_batches (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_batches_company_origin_created
            ON public.financial_automation_batches (company_id, origin_type, created_at);

        CREATE TABLE IF NOT EXISTS public.financial_automation_documents (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            batch_id INTEGER NOT NULL REFERENCES public.financial_automation_batches(id),
            file_name VARCHAR(255) NOT NULL,
            stored_relative_path VARCHAR(500),
            mime_type VARCHAR(120),
            file_size INTEGER,
            sha256 VARCHAR(64),
            extracted_text TEXT,
            preview_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );

        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_id
            ON public.financial_automation_documents (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_documents_company_batch
            ON public.financial_automation_documents (company_id, batch_id);

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
            amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            competence_date DATE,
            due_date DATE,
            confidence_score NUMERIC(5, 4),
            validation_notes TEXT,
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

        CREATE INDEX IF NOT EXISTS ix_financial_automation_history_company_id
            ON public.financial_automation_history (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_automation_history_company_record
            ON public.financial_automation_history (company_id, record_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.financial_automation_history;
        DROP TABLE IF EXISTS public.financial_automation_records;
        DROP TABLE IF EXISTS public.financial_automation_documents;
        DROP TABLE IF EXISTS public.financial_automation_batches;
        """
    )
