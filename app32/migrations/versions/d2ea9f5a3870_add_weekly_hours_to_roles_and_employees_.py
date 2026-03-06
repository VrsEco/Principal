"""add weekly_hours to roles and employees, and parent_role_id to roles

Revision ID: d2ea9f5a3870
Revises: 02ede27b3c02
Create Date: 2026-03-06 13:15:53.296761

Observação:
    A versão anterior desta migration foi gerada automaticamente com operações
    destrutivas incompatíveis com o histórico real do banco. Esta revisão foi
    regularizada para um comportamento aditivo, idempotente e seguro.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d2ea9f5a3870"
down_revision = "02ede27b3c02"
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
                   AND table_name = 'employees'
            ) THEN
                ALTER TABLE public.employees
                    ADD COLUMN IF NOT EXISTS weekly_hours NUMERIC(5, 2);
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'roles'
            ) THEN
                ALTER TABLE public.roles
                    ADD COLUMN IF NOT EXISTS weekly_hours NUMERIC(5, 2);

                ALTER TABLE public.roles
                    ADD COLUMN IF NOT EXISTS parent_role_id INTEGER;

                IF NOT EXISTS (
                    SELECT 1
                      FROM pg_constraint
                     WHERE conname = 'fk_roles_parent_role_id_roles'
                ) THEN
                    ALTER TABLE public.roles
                        ADD CONSTRAINT fk_roles_parent_role_id_roles
                        FOREIGN KEY (parent_role_id)
                        REFERENCES public.roles(id);
                END IF;
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
                   AND table_name = 'roles'
            ) THEN
                ALTER TABLE public.roles
                    DROP CONSTRAINT IF EXISTS fk_roles_parent_role_id_roles;

                ALTER TABLE public.roles
                    DROP COLUMN IF EXISTS parent_role_id;

                ALTER TABLE public.roles
                    DROP COLUMN IF EXISTS weekly_hours;
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = 'employees'
            ) THEN
                ALTER TABLE public.employees
                    DROP COLUMN IF EXISTS weekly_hours;
            END IF;
        END
        $$;
        """
    )
