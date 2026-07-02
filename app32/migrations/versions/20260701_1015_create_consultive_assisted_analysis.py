"""create consultive assisted analysis records

Revision ID: 20260701_1015
Revises: 20260630_1845
Create Date: 2026-07-01 10:15:00.000000
"""

from alembic import op


revision = "20260701_1015"
down_revision = "20260630_1845"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.consultive_assisted_analyses (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            front_key VARCHAR(40) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'received',

            ai_origin VARCHAR(120) NULL,
            responsible VARCHAR(160) NULL,
            diagnosis TEXT NOT NULL,
            benchmarks TEXT NULL,
            risks TEXT NULL,
            recommendations TEXT NULL,
            source_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,

            created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_consultive_assisted_analyses_front_key
                CHECK (front_key IN ('identity', 'processes', 'growth_plan', 'strategic_management')),
            CONSTRAINT ck_consultive_assisted_analyses_status
                CHECK (status IN ('received', 'under_review', 'validated', 'rejected', 'converted', 'archived'))
        );

        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analyses_company_front
            ON public.consultive_assisted_analyses(company_id, front_key);
        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analyses_company_status
            ON public.consultive_assisted_analyses(company_id, status);

        CREATE TABLE IF NOT EXISTS public.consultive_assisted_analysis_validations (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            analysis_id INTEGER NOT NULL REFERENCES public.consultive_assisted_analyses(id) ON DELETE CASCADE,
            squad VARCHAR(30) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            notes TEXT NULL,
            validated_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_consultive_assisted_analysis_validations_squad
                CHECK (squad IN ('client', 'versus', 'engineering')),
            CONSTRAINT ck_consultive_assisted_analysis_validations_status
                CHECK (status IN ('pending', 'validated', 'rejected', 'needs_adjustment')),
            CONSTRAINT uq_consultive_assisted_analysis_validations_analysis_squad
                UNIQUE (analysis_id, squad)
        );

        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analysis_validations_company_analysis
            ON public.consultive_assisted_analysis_validations(company_id, analysis_id);

        CREATE TABLE IF NOT EXISTS public.consultive_assisted_analysis_decisions (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            analysis_id INTEGER NOT NULL REFERENCES public.consultive_assisted_analyses(id) ON DELETE CASCADE,
            decision VARCHAR(30) NOT NULL,
            conversion_target VARCHAR(40) NOT NULL DEFAULT 'none',
            decision_reason TEXT NOT NULL,
            next_action TEXT NULL,
            governance_notes TEXT NULL,
            decided_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_consultive_assisted_analysis_decisions_decision
                CHECK (decision IN ('accept', 'adjust', 'reject', 'hold')),
            CONSTRAINT ck_consultive_assisted_analysis_decisions_conversion_target
                CHECK (conversion_target IN ('none', 'project', 'process', 'indicator', 'routine', 'business_review', 'urgent_need', 'structural_learning'))
        );

        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analysis_decisions_company_analysis
            ON public.consultive_assisted_analysis_decisions(company_id, analysis_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.consultive_assisted_analysis_decisions;
        DROP TABLE IF EXISTS public.consultive_assisted_analysis_validations;
        DROP TABLE IF EXISTS public.consultive_assisted_analyses;
        """
    )
