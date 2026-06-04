"""add customer portfolios catalog

Revision ID: 20260604_1400
Revises: 20260531_1800
Create Date: 2026-06-04 14:00:00
"""

from alembic import op


revision = "20260604_1400"
down_revision = "20260531_1800"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.financial_customer_portfolios (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            parent_id INTEGER REFERENCES public.financial_customer_portfolios(id) ON DELETE SET NULL,
            code VARCHAR(30) NOT NULL,
            name VARCHAR(120) NOT NULL,
            description TEXT,
            accepts_posting BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            CONSTRAINT uq_financial_customer_portfolios_company_code UNIQUE(company_id, code)
        );

        CREATE INDEX IF NOT EXISTS ix_financial_customer_portfolios_company_id
            ON public.financial_customer_portfolios(company_id);
        CREATE INDEX IF NOT EXISTS ix_financial_customer_portfolios_parent_id
            ON public.financial_customer_portfolios(parent_id);
        CREATE INDEX IF NOT EXISTS ix_financial_customer_portfolios_is_active
            ON public.financial_customer_portfolios(is_active);

        ALTER TABLE public.financial_counterparties
            ADD COLUMN IF NOT EXISTS customer_portfolio_id INTEGER;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_financial_counterparties_customer_portfolio'
            ) THEN
                ALTER TABLE public.financial_counterparties
                    ADD CONSTRAINT fk_financial_counterparties_customer_portfolio
                    FOREIGN KEY (customer_portfolio_id)
                    REFERENCES public.financial_customer_portfolios(id)
                    ON DELETE SET NULL;
            END IF;
        END$$;

        CREATE INDEX IF NOT EXISTS ix_financial_counterparties_customer_portfolio_id
            ON public.financial_counterparties(customer_portfolio_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_financial_counterparties_customer_portfolio_id;

        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_financial_counterparties_customer_portfolio'
            ) THEN
                ALTER TABLE public.financial_counterparties
                    DROP CONSTRAINT fk_financial_counterparties_customer_portfolio;
            END IF;
        END$$;

        ALTER TABLE public.financial_counterparties
            DROP COLUMN IF EXISTS customer_portfolio_id;

        DROP INDEX IF EXISTS public.ix_financial_customer_portfolios_is_active;
        DROP INDEX IF EXISTS public.ix_financial_customer_portfolios_parent_id;
        DROP INDEX IF EXISTS public.ix_financial_customer_portfolios_company_id;
        DROP TABLE IF EXISTS public.financial_customer_portfolios;
        """
    )
