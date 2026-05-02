"""create contract catalog items

Revision ID: 20260501_2245
Revises: 20260501_2015
Create Date: 2026-05-01 22:45:00
"""

from alembic import op


revision = "20260501_2245"
down_revision = "20260501_2015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.contract_catalog_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            parent_id INTEGER REFERENCES public.contract_catalog_items(id) ON DELETE SET NULL,
            code VARCHAR(30) NOT NULL,
            name VARCHAR(255) NOT NULL,
            item_kind VARCHAR(30) NOT NULL DEFAULT 'service',
            description TEXT,
            unit_code VARCHAR(20),
            accepts_contracting BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_catalog_items_company_code ON public.contract_catalog_items (company_id, code);
        CREATE INDEX IF NOT EXISTS ix_contract_catalog_items_company_id ON public.contract_catalog_items (company_id);
        CREATE INDEX IF NOT EXISTS ix_contract_catalog_items_parent_id ON public.contract_catalog_items (parent_id);

        ALTER TABLE public.contract_items
        ADD COLUMN IF NOT EXISTS contract_catalog_item_id INTEGER REFERENCES public.contract_catalog_items(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS ix_contract_items_contract_catalog_item_id ON public.contract_items (contract_catalog_item_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_contract_items_contract_catalog_item_id;
        ALTER TABLE public.contract_items
        DROP COLUMN IF EXISTS contract_catalog_item_id;

        DROP INDEX IF EXISTS public.ix_contract_catalog_items_parent_id;
        DROP INDEX IF EXISTS public.ix_contract_catalog_items_company_id;
        DROP INDEX IF EXISTS public.uq_contract_catalog_items_company_code;
        DROP TABLE IF EXISTS public.contract_catalog_items;
        """
    )
