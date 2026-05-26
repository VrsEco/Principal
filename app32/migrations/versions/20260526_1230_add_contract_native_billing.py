"""add contract native billing

Revision ID: 20260526_1230
Revises: 20260526_0900
Create Date: 2026-05-26 12:30:00
"""

from alembic import op


revision = "20260526_1230"
down_revision = "20260526_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.contract_native_billings (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            party_id INTEGER NOT NULL REFERENCES public.contract_parties(id) ON DELETE RESTRICT,
            billing_code VARCHAR(40) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'generated',
            source_type VARCHAR(30) NOT NULL DEFAULT 'native_contract',
            competence_start DATE NOT NULL,
            competence_end DATE NOT NULL,
            issue_date DATE NOT NULL,
            due_date DATE,
            gross_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
            net_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
            idempotency_key VARCHAR(160) NOT NULL,
            generated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_native_billings_company_code ON public.contract_native_billings (company_id, billing_code);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_contract_native_billings_company_idempotency ON public.contract_native_billings (company_id, idempotency_key);
        CREATE INDEX IF NOT EXISTS ix_contract_native_billings_company_id ON public.contract_native_billings (company_id);
        CREATE INDEX IF NOT EXISTS ix_contract_native_billings_contract_id ON public.contract_native_billings (contract_id);
        CREATE INDEX IF NOT EXISTS ix_contract_native_billings_party_id ON public.contract_native_billings (party_id);
        CREATE INDEX IF NOT EXISTS ix_contract_native_billings_competence_start ON public.contract_native_billings (competence_start);

        CREATE TABLE IF NOT EXISTS public.contract_native_billing_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_native_billing_id INTEGER NOT NULL REFERENCES public.contract_native_billings(id) ON DELETE CASCADE,
            contract_billing_item_id INTEGER REFERENCES public.contract_billing_items(id) ON DELETE SET NULL,
            contract_item_id INTEGER REFERENCES public.contract_items(id) ON DELETE SET NULL,
            description TEXT NOT NULL,
            amount NUMERIC(14,2) NOT NULL DEFAULT 0,
            competence_rule VARCHAR(60),
            due_rule VARCHAR(60),
            trigger_type VARCHAR(40),
            trigger_reference_date VARCHAR(40),
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_native_billing_items_company_id ON public.contract_native_billing_items (company_id);
        CREATE INDEX IF NOT EXISTS ix_contract_native_billing_items_billing_id ON public.contract_native_billing_items (contract_native_billing_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_contract_native_billing_items_billing_id;
        DROP INDEX IF EXISTS public.ix_contract_native_billing_items_company_id;
        DROP TABLE IF EXISTS public.contract_native_billing_items;

        DROP INDEX IF EXISTS public.ix_contract_native_billings_competence_start;
        DROP INDEX IF EXISTS public.ix_contract_native_billings_party_id;
        DROP INDEX IF EXISTS public.ix_contract_native_billings_contract_id;
        DROP INDEX IF EXISTS public.ix_contract_native_billings_company_id;
        DROP INDEX IF EXISTS public.uq_contract_native_billings_company_idempotency;
        DROP INDEX IF EXISTS public.uq_contract_native_billings_company_code;
        DROP TABLE IF EXISTS public.contract_native_billings;
        """
    )
