"""create consultive protocol library

Revision ID: 20260701_1030
Revises: 20260701_1015
Create Date: 2026-07-01 10:30:00.000000
"""

from alembic import op


revision = "20260701_1030"
down_revision = "20260701_1015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.consultive_protocols (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            front_key VARCHAR(40) NOT NULL,
            subphase_key VARCHAR(80) NULL,
            audience VARCHAR(40) NOT NULL DEFAULT 'ai_cli',
            depth_level VARCHAR(40) NOT NULL DEFAULT 'basic',
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            protocol_version VARCHAR(40) NOT NULL DEFAULT 'v1',
            title VARCHAR(255) NOT NULL,
            objective TEXT NULL,
            prompt_markdown TEXT NOT NULL,
            protocol_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            notes TEXT NULL,
            approved_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            approved_at TIMESTAMP WITHOUT TIME ZONE NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_consultive_protocols_status
                CHECK (status IN ('draft', 'active', 'archived')),
            CONSTRAINT ck_consultive_protocols_audience
                CHECK (audience IN ('ai_cli', 'client_squad', 'versus_squad', 'consultant')),
            CONSTRAINT ck_consultive_protocols_depth_level
                CHECK (depth_level IN ('basic', 'internal_diagnosis', 'deep_research', 'simulation'))
        );

        CREATE INDEX IF NOT EXISTS ix_consultive_protocols_resolution
            ON public.consultive_protocols(company_id, front_key, subphase_key, audience, status);
        CREATE INDEX IF NOT EXISTS ix_consultive_protocols_global_resolution
            ON public.consultive_protocols(front_key, subphase_key, audience, status);
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.consultive_protocols;")
