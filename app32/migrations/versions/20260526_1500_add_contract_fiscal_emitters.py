"""add contracting legal entities and expand contract fiscal terms

Revision ID: 20260526_1500
Revises: 20260526_1400
Create Date: 2026-05-26 15:00:00
"""

from alembic import op


revision = "20260526_1500"
down_revision = "20260526_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.contracting_legal_entities (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            code VARCHAR(30) NOT NULL,
            legal_name VARCHAR(255) NOT NULL,
            trade_name VARCHAR(255),
            cnpj VARCHAR(20) NOT NULL,
            municipal_registration VARCHAR(50),
            state_registration VARCHAR(50),
            tax_regime VARCHAR(50),
            cnae VARCHAR(30),
            service_city VARCHAR(120),
            city_code_ibge VARCHAR(20),
            uf VARCHAR(2),
            zip_code VARCHAR(20),
            address_line VARCHAR(255),
            address_number VARCHAR(30),
            district VARCHAR(120),
            complement VARCHAR(120),
            email VARCHAR(255),
            phone VARCHAR(50),
            nfs_provider VARCHAR(80),
            integration_mode VARCHAR(30) NOT NULL DEFAULT 'manual',
            api_profile_id INTEGER,
            spreadsheet_profile_id INTEGER,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_contracting_legal_entities_company_code UNIQUE(company_id, code),
            CONSTRAINT uq_contracting_legal_entities_company_cnpj UNIQUE(company_id, cnpj)
        );

        CREATE INDEX IF NOT EXISTS ix_contracting_legal_entities_company
            ON public.contracting_legal_entities(company_id);
        CREATE INDEX IF NOT EXISTS ix_contracting_legal_entities_active
            ON public.contracting_legal_entities(company_id, is_active);

        ALTER TABLE public.contracts
            ADD COLUMN IF NOT EXISTS contracting_legal_entity_id INTEGER REFERENCES public.contracting_legal_entities(id);
        CREATE INDEX IF NOT EXISTS ix_contracts_contracting_legal_entity_id
            ON public.contracts(company_id, contracting_legal_entity_id);

        ALTER TABLE public.contract_fiscal_terms
            ADD COLUMN IF NOT EXISTS contracting_legal_entity_id INTEGER REFERENCES public.contracting_legal_entities(id),
            ADD COLUMN IF NOT EXISTS integration_mode VARCHAR(30),
            ADD COLUMN IF NOT EXISTS nfs_provider VARCHAR(80),
            ADD COLUMN IF NOT EXISTS default_rps_series VARCHAR(30),
            ADD COLUMN IF NOT EXISTS service_code VARCHAR(60),
            ADD COLUMN IF NOT EXISTS service_list_item VARCHAR(60),
            ADD COLUMN IF NOT EXISTS operation_nature VARCHAR(120),
            ADD COLUMN IF NOT EXISTS iss_city VARCHAR(120),
            ADD COLUMN IF NOT EXISTS api_profile_id INTEGER,
            ADD COLUMN IF NOT EXISTS spreadsheet_profile_id INTEGER,
            ADD COLUMN IF NOT EXISTS withholding_flags JSONB NOT NULL DEFAULT '{}'::jsonb;

        CREATE INDEX IF NOT EXISTS ix_contract_fiscal_terms_contracting_entity
            ON public.contract_fiscal_terms(company_id, contracting_legal_entity_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_contract_fiscal_terms_contracting_entity;
        ALTER TABLE public.contract_fiscal_terms
            DROP COLUMN IF EXISTS withholding_flags,
            DROP COLUMN IF EXISTS spreadsheet_profile_id,
            DROP COLUMN IF EXISTS api_profile_id,
            DROP COLUMN IF EXISTS iss_city,
            DROP COLUMN IF EXISTS operation_nature,
            DROP COLUMN IF EXISTS service_list_item,
            DROP COLUMN IF EXISTS service_code,
            DROP COLUMN IF EXISTS default_rps_series,
            DROP COLUMN IF EXISTS nfs_provider,
            DROP COLUMN IF EXISTS integration_mode,
            DROP COLUMN IF EXISTS contracting_legal_entity_id;

        DROP INDEX IF EXISTS public.ix_contracts_contracting_legal_entity_id;
        ALTER TABLE public.contracts DROP COLUMN IF EXISTS contracting_legal_entity_id;

        DROP INDEX IF EXISTS public.ix_contracting_legal_entities_active;
        DROP INDEX IF EXISTS public.ix_contracting_legal_entities_company;
        DROP TABLE IF EXISTS public.contracting_legal_entities;
        """
    )
