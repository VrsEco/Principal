"""create urgent need, business review and structural learning overlays

Revision ID: 20260630_1845
Revises: 20260614_1200
Create Date: 2026-06-30 18:45:00.000000
"""

from alembic import op


revision = "20260630_1845"
down_revision = "20260614_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.urgent_need_overlays (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'inbox',
            urgency_level VARCHAR(20) NOT NULL DEFAULT 'medium',
            criticality_level VARCHAR(40) NOT NULL DEFAULT 'operational',
            origin_channel VARCHAR(60) NULL,
            origin_summary TEXT NULL,

            project_id INTEGER NULL REFERENCES public.projects(id) ON DELETE SET NULL,
            project_task_id INTEGER NULL REFERENCES public.project_tasks(id) ON DELETE SET NULL,
            process_id INTEGER NULL REFERENCES public.processes(id) ON DELETE SET NULL,
            process_instance_id INTEGER NULL REFERENCES public.process_instances(id) ON DELETE SET NULL,
            routine_id INTEGER NULL REFERENCES public.routines(id) ON DELETE SET NULL,
            indicator_id INTEGER NULL REFERENCES public.indicators(id) ON DELETE SET NULL,
            meeting_id INTEGER NULL REFERENCES public.meetings(id) ON DELETE SET NULL,
            occurrence_id INTEGER NULL REFERENCES public.occurrences(id) ON DELETE SET NULL,
            financial_ref_id INTEGER NULL,

            source_type VARCHAR(80) NULL,
            source_ref_id VARCHAR(120) NULL,
            source_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,

            business_impact_summary TEXT NULL,
            operational_impact_summary TEXT NULL,
            risk_summary TEXT NULL,
            decision_status VARCHAR(40) NOT NULL DEFAULT 'pending',
            decision_summary TEXT NULL,

            responsible_employee_id INTEGER NULL REFERENCES public.employees(id) ON DELETE SET NULL,
            created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            closed_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,

            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMP WITHOUT TIME ZONE NULL,

            CONSTRAINT ck_urgent_need_overlays_status
                CHECK (status IN ('inbox', 'triage', 'in_review', 'decided', 'in_execution', 'closed', 'cancelled')),
            CONSTRAINT ck_urgent_need_overlays_urgency_level
                CHECK (urgency_level IN ('low', 'medium', 'high', 'critical')),
            CONSTRAINT ck_urgent_need_overlays_criticality_level
                CHECK (criticality_level IN ('operational', 'managerial', 'strategic', 'legal_regulatory', 'financial', 'reputational')),
            CONSTRAINT ck_urgent_need_overlays_has_canonical_link
                CHECK (
                    project_id IS NOT NULL OR project_task_id IS NOT NULL OR process_id IS NOT NULL OR
                    process_instance_id IS NOT NULL OR routine_id IS NOT NULL OR indicator_id IS NOT NULL OR
                    meeting_id IS NOT NULL OR occurrence_id IS NOT NULL
                )
        );

        CREATE INDEX IF NOT EXISTS ix_urgent_need_overlays_company_status
            ON public.urgent_need_overlays(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_urgent_need_overlays_company_urgency
            ON public.urgent_need_overlays(company_id, urgency_level);
        CREATE INDEX IF NOT EXISTS ix_urgent_need_overlays_company_project
            ON public.urgent_need_overlays(company_id, project_id);
        CREATE INDEX IF NOT EXISTS ix_urgent_need_overlays_company_task
            ON public.urgent_need_overlays(company_id, project_task_id);
        CREATE INDEX IF NOT EXISTS ix_urgent_need_overlays_company_process
            ON public.urgent_need_overlays(company_id, process_id);
        CREATE INDEX IF NOT EXISTS ix_urgent_need_overlays_company_indicator
            ON public.urgent_need_overlays(company_id, indicator_id);

        CREATE TABLE IF NOT EXISTS public.business_review_records (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            review_type VARCHAR(40) NOT NULL DEFAULT 'urgent_need',
            status VARCHAR(30) NOT NULL DEFAULT 'draft',

            urgent_need_id INTEGER NULL REFERENCES public.urgent_need_overlays(id) ON DELETE SET NULL,
            project_id INTEGER NULL REFERENCES public.projects(id) ON DELETE SET NULL,
            project_task_id INTEGER NULL REFERENCES public.project_tasks(id) ON DELETE SET NULL,
            process_id INTEGER NULL REFERENCES public.processes(id) ON DELETE SET NULL,
            indicator_id INTEGER NULL REFERENCES public.indicators(id) ON DELETE SET NULL,
            meeting_id INTEGER NULL REFERENCES public.meetings(id) ON DELETE SET NULL,

            cost_to_act NUMERIC(14, 2) NULL,
            cost_to_not_act NUMERIC(14, 2) NULL,
            required_investment NUMERIC(14, 2) NULL,
            expected_gain NUMERIC(14, 2) NULL,
            expected_return NUMERIC(14, 2) NULL,
            risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
            risk_acceptance_decision BOOLEAN NOT NULL DEFAULT FALSE,
            risk_acceptance_reason TEXT NULL,

            decision_summary TEXT NULL,
            structural_learning_summary TEXT NULL,
            next_action TEXT NULL,

            responsible_employee_id INTEGER NULL REFERENCES public.employees(id) ON DELETE SET NULL,
            reviewed_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,

            reviewed_at TIMESTAMP WITHOUT TIME ZONE NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMP WITHOUT TIME ZONE NULL,

            CONSTRAINT ck_business_review_records_review_type
                CHECK (review_type IN ('urgent_need', 'project_investment', 'process_correction', 'risk_acceptance', 'strategic_decision', 'financial_impact')),
            CONSTRAINT ck_business_review_records_status
                CHECK (status IN ('draft', 'in_analysis', 'pending_decision', 'approved', 'risk_accepted', 'rejected', 'closed')),
            CONSTRAINT ck_business_review_records_risk_reason
                CHECK (risk_acceptance_decision IS DISTINCT FROM TRUE OR btrim(risk_acceptance_reason) <> '')
        );

        CREATE INDEX IF NOT EXISTS ix_business_review_records_company_status
            ON public.business_review_records(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_business_review_records_company_type
            ON public.business_review_records(company_id, review_type);
        CREATE INDEX IF NOT EXISTS ix_business_review_records_company_urgent_need
            ON public.business_review_records(company_id, urgent_need_id);
        CREATE INDEX IF NOT EXISTS ix_business_review_records_company_project
            ON public.business_review_records(company_id, project_id);
        CREATE INDEX IF NOT EXISTS ix_business_review_records_company_process
            ON public.business_review_records(company_id, process_id);

        CREATE TABLE IF NOT EXISTS public.structural_learning_links (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            business_review_id INTEGER NOT NULL REFERENCES public.business_review_records(id) ON DELETE CASCADE,
            urgent_need_id INTEGER NULL REFERENCES public.urgent_need_overlays(id) ON DELETE SET NULL,

            target_project_id INTEGER NULL REFERENCES public.projects(id) ON DELETE SET NULL,
            target_project_task_id INTEGER NULL REFERENCES public.project_tasks(id) ON DELETE SET NULL,
            target_process_id INTEGER NULL REFERENCES public.processes(id) ON DELETE SET NULL,
            target_routine_id INTEGER NULL REFERENCES public.routines(id) ON DELETE SET NULL,
            target_indicator_id INTEGER NULL REFERENCES public.indicators(id) ON DELETE SET NULL,
            target_meeting_id INTEGER NULL REFERENCES public.meetings(id) ON DELETE SET NULL,

            learning_type VARCHAR(40) NOT NULL,
            action_decision VARCHAR(40) NOT NULL DEFAULT 'recommended',
            accepted_risk_reason TEXT NULL,
            recommended_change TEXT NULL,

            created_project_id INTEGER NULL REFERENCES public.projects(id) ON DELETE SET NULL,
            created_task_id INTEGER NULL REFERENCES public.project_tasks(id) ON DELETE SET NULL,

            created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_structural_learning_links_learning_type
                CHECK (learning_type IN ('process_change', 'routine_change', 'indicator_change', 'control_change', 'policy_change', 'project_creation', 'task_creation', 'risk_acceptance', 'no_structural_action')),
            CONSTRAINT ck_structural_learning_links_action_decision
                CHECK (action_decision IN ('recommended', 'approved', 'rejected', 'risk_accepted', 'converted_to_project', 'converted_to_task', 'closed_no_action')),
            CONSTRAINT ck_structural_learning_links_risk_reason
                CHECK (action_decision != 'risk_accepted' OR btrim(accepted_risk_reason) <> '')
        );

        CREATE INDEX IF NOT EXISTS ix_structural_learning_links_company_review
            ON public.structural_learning_links(company_id, business_review_id);
        CREATE INDEX IF NOT EXISTS ix_structural_learning_links_company_urgent_need
            ON public.structural_learning_links(company_id, urgent_need_id);
        CREATE INDEX IF NOT EXISTS ix_structural_learning_links_company_process
            ON public.structural_learning_links(company_id, target_process_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.structural_learning_links;
        DROP TABLE IF EXISTS public.business_review_records;
        DROP TABLE IF EXISTS public.urgent_need_overlays;
        """
    )
