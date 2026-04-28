"""create financial manual domains

Revision ID: 20260427_2130
Revises: 20260425_1030
Create Date: 2026-04-27 21:30:00
"""

from alembic import op


revision = "20260427_2130"
down_revision = "20260425_1030"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.financial_manual_domains (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            domain_type VARCHAR(20) NOT NULL,
            code VARCHAR(40),
            name VARCHAR(160) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            is_default_suggestion BOOLEAN NOT NULL DEFAULT FALSE,
            notes TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            CONSTRAINT uq_financial_manual_domains_company_type_code UNIQUE (company_id, domain_type, code),
            CONSTRAINT ck_financial_manual_domains_domain_type CHECK (domain_type IN ('project', 'process'))
        );

        CREATE INDEX IF NOT EXISTS ix_financial_manual_domains_company_id
            ON public.financial_manual_domains (company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_manual_domains_domain_type
            ON public.financial_manual_domains (domain_type);
        CREATE INDEX IF NOT EXISTS ix_financial_manual_domains_is_active
            ON public.financial_manual_domains (is_active);
        CREATE INDEX IF NOT EXISTS ix_financial_manual_domains_is_enabled
            ON public.financial_manual_domains (is_enabled);
        CREATE INDEX IF NOT EXISTS ix_financial_manual_domains_is_default_suggestion
            ON public.financial_manual_domains (is_default_suggestion);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_financial_manual_domains_is_default_suggestion;
        DROP INDEX IF EXISTS public.ix_financial_manual_domains_is_enabled;
        DROP INDEX IF EXISTS public.ix_financial_manual_domains_is_active;
        DROP INDEX IF EXISTS public.ix_financial_manual_domains_domain_type;
        DROP INDEX IF EXISTS public.ix_financial_manual_domains_company_id;
        DROP TABLE IF EXISTS public.financial_manual_domains;
        """
    )
