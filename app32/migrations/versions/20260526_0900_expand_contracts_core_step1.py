"""expand contracts core step1

Revision ID: 20260526_0900
Revises: 20260520_2300
Create Date: 2026-05-26 09:00:00
"""

from alembic import op


revision = "20260526_0900"
down_revision = "20260520_2300"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.contracts
            ADD COLUMN IF NOT EXISTS manager_employee_id INTEGER REFERENCES public.employees(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS renewal_date DATE,
            ADD COLUMN IF NOT EXISTS adjustment_date DATE,
            ADD COLUMN IF NOT EXISTS termination_date DATE,
            ADD COLUMN IF NOT EXISTS end_reason VARCHAR(40),
            ADD COLUMN IF NOT EXISTS previous_contract_id INTEGER REFERENCES public.contracts(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS ix_contracts_manager_employee_id ON public.contracts (manager_employee_id);
        CREATE INDEX IF NOT EXISTS ix_contracts_previous_contract_id ON public.contracts (previous_contract_id);
        CREATE INDEX IF NOT EXISTS ix_contracts_renewal_date ON public.contracts (renewal_date);
        CREATE INDEX IF NOT EXISTS ix_contracts_adjustment_date ON public.contracts (adjustment_date);
        CREATE INDEX IF NOT EXISTS ix_contracts_termination_date ON public.contracts (termination_date);

        CREATE TABLE IF NOT EXISTS public.contract_clauses (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            clause_type VARCHAR(40),
            title VARCHAR(255),
            content TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_clauses_contract_id ON public.contract_clauses (contract_id);
        CREATE INDEX IF NOT EXISTS ix_contract_clauses_company_id ON public.contract_clauses (company_id);

        CREATE TABLE IF NOT EXISTS public.contract_notes (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            note_type VARCHAR(40) NOT NULL DEFAULT 'general',
            note_text TEXT NOT NULL,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_notes_contract_id ON public.contract_notes (contract_id);
        CREATE INDEX IF NOT EXISTS ix_contract_notes_company_id ON public.contract_notes (company_id);

        CREATE TABLE IF NOT EXISTS public.contract_events (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            contract_id INTEGER NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
            event_type VARCHAR(60) NOT NULL,
            description TEXT,
            event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_contract_events_contract_id ON public.contract_events (contract_id);
        CREATE INDEX IF NOT EXISTS ix_contract_events_company_id ON public.contract_events (company_id);
        CREATE INDEX IF NOT EXISTS ix_contract_events_event_type ON public.contract_events (event_type);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_contract_events_event_type;
        DROP INDEX IF EXISTS public.ix_contract_events_company_id;
        DROP INDEX IF EXISTS public.ix_contract_events_contract_id;
        DROP TABLE IF EXISTS public.contract_events;

        DROP INDEX IF EXISTS public.ix_contract_notes_company_id;
        DROP INDEX IF EXISTS public.ix_contract_notes_contract_id;
        DROP TABLE IF EXISTS public.contract_notes;

        DROP INDEX IF EXISTS public.ix_contract_clauses_company_id;
        DROP INDEX IF EXISTS public.ix_contract_clauses_contract_id;
        DROP TABLE IF EXISTS public.contract_clauses;

        DROP INDEX IF EXISTS public.ix_contracts_termination_date;
        DROP INDEX IF EXISTS public.ix_contracts_adjustment_date;
        DROP INDEX IF EXISTS public.ix_contracts_renewal_date;
        DROP INDEX IF EXISTS public.ix_contracts_previous_contract_id;
        DROP INDEX IF EXISTS public.ix_contracts_manager_employee_id;

        ALTER TABLE public.contracts
            DROP COLUMN IF EXISTS previous_contract_id,
            DROP COLUMN IF EXISTS end_reason,
            DROP COLUMN IF EXISTS termination_date,
            DROP COLUMN IF EXISTS adjustment_date,
            DROP COLUMN IF EXISTS renewal_date,
            DROP COLUMN IF EXISTS manager_employee_id;
        """
    )
