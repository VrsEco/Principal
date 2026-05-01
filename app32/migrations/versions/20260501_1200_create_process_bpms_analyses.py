"""create process bpms analyses

Revision ID: 20260501_1200
Revises: 20260430_2355
Create Date: 2026-05-01 12:00:00
"""

from alembic import op

revision = "20260501_1200"
down_revision = "20260430_2355"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.process_bpms_analyses (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_id INTEGER REFERENCES public.processes(id) ON DELETE SET NULL,
            title VARCHAR(255) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            scope VARCHAR(30) NOT NULL DEFAULT 'empresa',
            objective TEXT,
            goal TEXT,
            problem_statement TEXT,
            expected_result TEXT,
            current_indicators TEXT,
            missing_indicators TEXT,
            success_measurement TEXT,
            as_is_summary TEXT,
            as_is_steps TEXT,
            as_is_exceptions TEXT,
            bottlenecks TEXT,
            operational_risks TEXT,
            dependencies TEXT,
            to_be_summary TEXT,
            to_be_steps TEXT,
            controls TEXT,
            expected_automation TEXT,
            desired_indicators TEXT,
            app_adherence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            identified_gaps TEXT,
            gap_classification_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            prioritization_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            architectural_impact TEXT,
            requires_architect BOOLEAN NOT NULL DEFAULT FALSE,
            requires_backend_service BOOLEAN NOT NULL DEFAULT FALSE,
            requires_backend_api BOOLEAN NOT NULL DEFAULT FALSE,
            requires_ai_engineer BOOLEAN NOT NULL DEFAULT FALSE,
            requires_dba BOOLEAN NOT NULL DEFAULT FALSE,
            requires_qa_automation BOOLEAN NOT NULL DEFAULT FALSE,
            governance_notes TEXT,
            recommendation_summary TEXT,
            implement_now TEXT,
            parameterize_now TEXT,
            customize_later TEXT,
            develop_for_real TEXT,
            not_now TEXT,
            next_action TEXT,
            lead_specialist VARCHAR(120),
            dependencies_before_execution TEXT,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_process_bpms_analyses_company_id ON public.process_bpms_analyses (company_id);
        CREATE INDEX IF NOT EXISTS ix_process_bpms_analyses_process_id ON public.process_bpms_analyses (process_id);
        CREATE INDEX IF NOT EXISTS ix_process_bpms_analyses_company_process ON public.process_bpms_analyses (company_id, process_id);
        CREATE INDEX IF NOT EXISTS ix_process_bpms_analyses_company_updated ON public.process_bpms_analyses (company_id, updated_at DESC);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_process_bpms_analyses_company_updated;
        DROP INDEX IF EXISTS public.ix_process_bpms_analyses_company_process;
        DROP INDEX IF EXISTS public.ix_process_bpms_analyses_process_id;
        DROP INDEX IF EXISTS public.ix_process_bpms_analyses_company_id;
        DROP TABLE IF EXISTS public.process_bpms_analyses;
        """
    )
