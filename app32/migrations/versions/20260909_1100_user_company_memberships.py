"""separa vínculo usuário-empresa do cadastro de colaborador

Revision ID: 20260909_1100
Revises: 6c9b3e8f4a21
Create Date: 2026-09-09 21:00:00.000000
"""

from alembic import op


revision = "20260909_1100"
down_revision = "6c9b3e8f4a21"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.user_company_memberships (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            access_profile VARCHAR(20) NOT NULL DEFAULT 'collaborator',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_company_memberships_user_company UNIQUE (user_id, company_id),
            CONSTRAINT ck_user_company_memberships_access_profile
                CHECK (access_profile IN ('administrator', 'client', 'collaborator'))
        );

        CREATE INDEX IF NOT EXISTS ix_user_company_memberships_user_id
            ON public.user_company_memberships(user_id);
        CREATE INDEX IF NOT EXISTS ix_user_company_memberships_company_id
            ON public.user_company_memberships(company_id);

        INSERT INTO public.user_company_memberships (
            user_id, company_id, access_profile, is_active, created_at, updated_at
        )
        SELECT
            e.user_id,
            e.company_id,
            CASE
                WHEN lower(coalesce(u.role, '')) IN ('admin', 'administrator') THEN 'administrator'
                WHEN lower(coalesce(u.role, '')) = 'client' THEN 'client'
                ELSE 'collaborator'
            END,
            CASE WHEN lower(coalesce(e.status, 'active')) IN ('inactive', 'inativo') THEN FALSE ELSE TRUE END,
            NOW(), NOW()
        FROM public.employees e
        INNER JOIN public.users u ON u.id = e.user_id
        WHERE e.user_id IS NOT NULL
        ON CONFLICT (user_id, company_id) DO NOTHING;
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.user_company_memberships;")
