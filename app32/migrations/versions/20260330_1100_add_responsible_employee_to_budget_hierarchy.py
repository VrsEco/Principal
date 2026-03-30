"""add responsible employee to budget hierarchy

Revision ID: 20260330_1100
Revises: 20260329_2030
Create Date: 2026-03-30 11:00:00
"""

from alembic import op


revision = "20260330_1100"
down_revision = "20260329_2030"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'financial_budget_versions'
            ) THEN
                ALTER TABLE public.financial_budget_versions
                    ADD COLUMN IF NOT EXISTS responsible_employee_id INTEGER;

                IF NOT EXISTS (
                    SELECT 1
                      FROM pg_constraint
                     WHERE conname = 'fk_financial_budget_versions_responsible_employee_id_employees'
                ) THEN
                    ALTER TABLE public.financial_budget_versions
                        ADD CONSTRAINT fk_financial_budget_versions_responsible_employee_id_employees
                        FOREIGN KEY (responsible_employee_id)
                        REFERENCES public.employees(id)
                        ON DELETE SET NULL;
                END IF;

                CREATE INDEX IF NOT EXISTS ix_financial_budget_versions_responsible_employee_id
                    ON public.financial_budget_versions (responsible_employee_id);
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'financial_budget_lines'
            ) THEN
                ALTER TABLE public.financial_budget_lines
                    ADD COLUMN IF NOT EXISTS responsible_employee_id INTEGER;

                IF NOT EXISTS (
                    SELECT 1
                      FROM pg_constraint
                     WHERE conname = 'fk_financial_budget_lines_responsible_employee_id_employees'
                ) THEN
                    ALTER TABLE public.financial_budget_lines
                        ADD CONSTRAINT fk_financial_budget_lines_responsible_employee_id_employees
                        FOREIGN KEY (responsible_employee_id)
                        REFERENCES public.employees(id)
                        ON DELETE SET NULL;
                END IF;

                CREATE INDEX IF NOT EXISTS ix_financial_budget_lines_responsible_employee_id
                    ON public.financial_budget_lines (responsible_employee_id);
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'financial_budget_contracts'
            ) THEN
                ALTER TABLE public.financial_budget_contracts
                    ADD COLUMN IF NOT EXISTS responsible_employee_id INTEGER;

                IF NOT EXISTS (
                    SELECT 1
                      FROM pg_constraint
                     WHERE conname = 'fk_financial_budget_contracts_responsible_employee_id_employees'
                ) THEN
                    ALTER TABLE public.financial_budget_contracts
                        ADD CONSTRAINT fk_financial_budget_contracts_responsible_employee_id_employees
                        FOREIGN KEY (responsible_employee_id)
                        REFERENCES public.employees(id)
                        ON DELETE SET NULL;
                END IF;

                CREATE INDEX IF NOT EXISTS ix_financial_budget_contracts_responsible_employee_id
                    ON public.financial_budget_contracts (responsible_employee_id);
            END IF;
        END
        $$;
        """
    )


def downgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'financial_budget_contracts'
            ) THEN
                ALTER TABLE public.financial_budget_contracts
                    DROP CONSTRAINT IF EXISTS fk_financial_budget_contracts_responsible_employee_id_employees;

                DROP INDEX IF EXISTS public.ix_financial_budget_contracts_responsible_employee_id;

                ALTER TABLE public.financial_budget_contracts
                    DROP COLUMN IF EXISTS responsible_employee_id;
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'financial_budget_lines'
            ) THEN
                ALTER TABLE public.financial_budget_lines
                    DROP CONSTRAINT IF EXISTS fk_financial_budget_lines_responsible_employee_id_employees;

                DROP INDEX IF EXISTS public.ix_financial_budget_lines_responsible_employee_id;

                ALTER TABLE public.financial_budget_lines
                    DROP COLUMN IF EXISTS responsible_employee_id;
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'financial_budget_versions'
            ) THEN
                ALTER TABLE public.financial_budget_versions
                    DROP CONSTRAINT IF EXISTS fk_financial_budget_versions_responsible_employee_id_employees;

                DROP INDEX IF EXISTS public.ix_financial_budget_versions_responsible_employee_id;

                ALTER TABLE public.financial_budget_versions
                    DROP COLUMN IF EXISTS responsible_employee_id;
            END IF;
        END
        $$;
        """
    )
