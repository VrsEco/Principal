"""create contracts core

Revision ID: 20260501_1530
Revises: 20260501_1200
Create Date: 2026-05-01 15:30:00
"""

from alembic import op


revision = "20260501_1530"
down_revision = "20260501_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.contract_parties (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            financial_counterparty_id INTEGER REFERENCES public.financial_counterparties(id) ON DELETE SET NULL,
            code VARCHAR(30) NOT NULL,
            name VARCHAR(255) NOT NULL,
            legal_name VARCHAR(255),
            document_type VARCHAR(20),
            document_number VARCHAR(50),
            email VARCHAR(255),
            phone VARCHAR(50),
            is_customer BOOLEAN NOT NULL DEFAULT FALSE,
            is_supplier BOOLEAN NOT NULL DEFAULT FALSE,
            status VARCHAR(30) NOT NULL DEFAULT 'active',
            notes TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_parties_company_code ON public.contract_parties (company_id, code);
        CREATE INDEX IF NOT EXISTS ix_contract_parties_company_id ON public.contract_parties (company_id);
        CREATE INDEX IF NOT EXISTS ix_contract_parties_document_number ON public.contract_parties (document_number);

        CREATE TABLE IF NOT EXISTS public.contracts (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            party_id INTEGER NOT NULL REFERENCES public.contract_parties(id) ON DELETE RESTRICT,
            code VARCHAR(30) NOT NULL,
            title VARCHAR(255) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            contract_type VARCHAR(60),
            currency_code VARCHAR(3) NOT NULL DEFAULT 'BRL',
            signed_at DATE,
            service_start_at DATE,
            service_end_at DATE,
            billing_start_at DATE,
            billing_end_at DATE,
            periodicity VARCHAR(30),
            competence_rule VARCHAR(60),
            due_rule VARCHAR(60),
            renewal_rule VARCHAR(60),
            notes TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contracts_company_code ON public.contracts (company_id, code);
        CREATE INDEX IF NOT EXISTS ix_contracts_company_id ON public.contracts (company_id);
        CREATE INDEX IF NOT EXISTS ix_contracts_party_id ON public.contracts (party_id);
        CREATE INDEX IF NOT EXISTS ix_contracts_status ON public.contracts (status);

        CREATE TABLE IF NOT EXISTS public.contract_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            item_code VARCHAR(30),
            item_type VARCHAR(40),
            description TEXT NOT NULL,
            quantity NUMERIC(14,2) NOT NULL DEFAULT 0,
            unit_code VARCHAR(20),
            unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
            total_price NUMERIC(14,2) NOT NULL DEFAULT 0,
            order_index INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_items_contract_id ON public.contract_items (contract_id);

        CREATE TABLE IF NOT EXISTS public.contract_billing_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            contract_item_id INTEGER REFERENCES public.contract_items(id) ON DELETE SET NULL,
            billing_code VARCHAR(30),
            description TEXT NOT NULL,
            amount NUMERIC(14,2) NOT NULL DEFAULT 0,
            billing_periodicity VARCHAR(30),
            competence_rule VARCHAR(60),
            due_rule VARCHAR(60),
            trigger_type VARCHAR(40),
            trigger_reference_date VARCHAR(40),
            is_recurring BOOLEAN NOT NULL DEFAULT TRUE,
            order_index INTEGER NOT NULL DEFAULT 0,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_billing_items_contract_id ON public.contract_billing_items (contract_id);

        CREATE TABLE IF NOT EXISTS public.contract_financial_terms (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            default_bank_account_id INTEGER REFERENCES public.financial_bank_accounts(id) ON DELETE SET NULL,
            default_payment_method_id INTEGER REFERENCES public.financial_payment_methods(id) ON DELETE SET NULL,
            correction_index_id INTEGER REFERENCES public.financial_correction_indexes(id) ON DELETE SET NULL,
            payment_term_type VARCHAR(40),
            payment_term_days INTEGER,
            billing_method VARCHAR(40),
            pricing_model VARCHAR(40),
            adjustment_rule VARCHAR(60),
            notes TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_financial_terms_contract_id ON public.contract_financial_terms (contract_id);

        CREATE TABLE IF NOT EXISTS public.contract_fiscal_terms (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            fiscal_profile_code VARCHAR(40),
            service_city VARCHAR(120),
            tax_nature VARCHAR(120),
            tax_observation TEXT,
            notes TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_fiscal_terms_contract_id ON public.contract_fiscal_terms (contract_id);

        CREATE TABLE IF NOT EXISTS public.contract_retentions (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            retention_type VARCHAR(40) NOT NULL,
            calculation_mode VARCHAR(20),
            rate_percent NUMERIC(10,4),
            fixed_amount NUMERIC(14,2),
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_retentions_contract_id ON public.contract_retentions (contract_id);

        CREATE TABLE IF NOT EXISTS public.contract_triggers (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            trigger_type VARCHAR(40) NOT NULL,
            reference_date_type VARCHAR(40),
            reference_date_value DATE,
            offset_days INTEGER,
            periodicity VARCHAR(30),
            alert_before_days INTEGER,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_triggers_contract_id ON public.contract_triggers (contract_id);

        CREATE TABLE IF NOT EXISTS public.contract_documents (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            document_type VARCHAR(40) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            mime_type VARCHAR(120),
            document_version VARCHAR(30),
            source VARCHAR(30) NOT NULL DEFAULT 'manual',
            is_signed_version BOOLEAN NOT NULL DEFAULT FALSE,
            uploaded_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            uploaded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        CREATE INDEX IF NOT EXISTS ix_contract_documents_contract_id ON public.contract_documents (contract_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_contract_documents_contract_id;
        DROP TABLE IF EXISTS public.contract_documents;
        DROP INDEX IF EXISTS public.ix_contract_triggers_contract_id;
        DROP TABLE IF EXISTS public.contract_triggers;
        DROP INDEX IF EXISTS public.ix_contract_retentions_contract_id;
        DROP TABLE IF EXISTS public.contract_retentions;
        DROP INDEX IF EXISTS public.uq_contract_fiscal_terms_contract_id;
        DROP TABLE IF EXISTS public.contract_fiscal_terms;
        DROP INDEX IF EXISTS public.uq_contract_financial_terms_contract_id;
        DROP TABLE IF EXISTS public.contract_financial_terms;
        DROP INDEX IF EXISTS public.ix_contract_billing_items_contract_id;
        DROP TABLE IF EXISTS public.contract_billing_items;
        DROP INDEX IF EXISTS public.ix_contract_items_contract_id;
        DROP TABLE IF EXISTS public.contract_items;
        DROP INDEX IF EXISTS public.ix_contracts_status;
        DROP INDEX IF EXISTS public.ix_contracts_party_id;
        DROP INDEX IF EXISTS public.ix_contracts_company_id;
        DROP INDEX IF EXISTS public.uq_contracts_company_code;
        DROP TABLE IF EXISTS public.contracts;
        DROP INDEX IF EXISTS public.ix_contract_parties_document_number;
        DROP INDEX IF EXISTS public.ix_contract_parties_company_id;
        DROP INDEX IF EXISTS public.uq_contract_parties_company_code;
        DROP TABLE IF EXISTS public.contract_parties;
        """
    )
