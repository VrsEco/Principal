"""add internal audit wave3 workpapers findings

Revision ID: 20260719_1030
Revises: 20260719_0900
Create Date: 2026-07-19 10:30:00
"""

from alembic import op


revision = "20260719_1030"
down_revision = "20260719_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.audit_workpapers (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            execution_id INTEGER REFERENCES public.audit_executions(id) ON DELETE SET NULL,
            execution_item_id INTEGER REFERENCES public.audit_execution_items(id) ON DELETE SET NULL,
            audit_point_id INTEGER REFERENCES public.audit_points(id) ON DELETE SET NULL,
            auditor_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            comments TEXT,
            conclusion TEXT,
            alert_notes TEXT,
            evidence_summary TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_audit_workpapers_company_id ON public.audit_workpapers(company_id);
        CREATE INDEX IF NOT EXISTS ix_audit_workpapers_company_execution ON public.audit_workpapers(company_id, execution_id);
        CREATE INDEX IF NOT EXISTS ix_audit_workpapers_company_item ON public.audit_workpapers(company_id, execution_item_id);
        CREATE INDEX IF NOT EXISTS ix_audit_workpapers_company_point ON public.audit_workpapers(company_id, audit_point_id);
        CREATE INDEX IF NOT EXISTS ix_audit_workpapers_company_auditor ON public.audit_workpapers(company_id, auditor_user_id);

        CREATE TABLE IF NOT EXISTS public.audit_findings (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            audit_point_id INTEGER REFERENCES public.audit_points(id) ON DELETE SET NULL,
            execution_id INTEGER REFERENCES public.audit_executions(id) ON DELETE SET NULL,
            execution_item_id INTEGER REFERENCES public.audit_execution_items(id) ON DELETE SET NULL,
            title VARCHAR(255) NOT NULL,
            condition_text TEXT,
            criterion_text TEXT,
            cause_text TEXT,
            effect_text TEXT,
            recommendation_text TEXT,
            severity VARCHAR(30) NOT NULL DEFAULT 'medium',
            status VARCHAR(40) NOT NULL DEFAULT 'open',
            responsible_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            due_date DATE,
            project_id INTEGER REFERENCES public.projects(id) ON DELETE SET NULL,
            task_id INTEGER REFERENCES public.project_tasks(id) ON DELETE SET NULL,
            alignment_meeting_id INTEGER REFERENCES public.meetings(id) ON DELETE SET NULL,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_findings_severity CHECK (severity IN ('low','medium','high','critical')),
            CONSTRAINT ck_audit_findings_status CHECK (status IN ('open','action_linked','in_follow_up','resolved','closed','cancelled'))
        );
        CREATE INDEX IF NOT EXISTS ix_audit_findings_company_id ON public.audit_findings(company_id);
        CREATE INDEX IF NOT EXISTS ix_audit_findings_company_status ON public.audit_findings(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_audit_findings_company_severity ON public.audit_findings(company_id, severity);
        CREATE INDEX IF NOT EXISTS ix_audit_findings_company_point ON public.audit_findings(company_id, audit_point_id);
        CREATE INDEX IF NOT EXISTS ix_audit_findings_company_project ON public.audit_findings(company_id, project_id);
        CREATE INDEX IF NOT EXISTS ix_audit_findings_company_task ON public.audit_findings(company_id, task_id);

        CREATE TABLE IF NOT EXISTS public.audit_evidence_links (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            workpaper_id INTEGER REFERENCES public.audit_workpapers(id) ON DELETE CASCADE,
            finding_id INTEGER REFERENCES public.audit_findings(id) ON DELETE CASCADE,
            evidence_type VARCHAR(30) NOT NULL DEFAULT 'comment',
            source_module VARCHAR(60),
            source_id INTEGER,
            file_path TEXT,
            caption TEXT,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_evidence_links_type CHECK (evidence_type IN ('file','image','link','system_record','comment')),
            CONSTRAINT ck_audit_evidence_links_parent CHECK (workpaper_id IS NOT NULL OR finding_id IS NOT NULL)
        );
        CREATE INDEX IF NOT EXISTS ix_audit_evidence_links_company_id ON public.audit_evidence_links(company_id);
        CREATE INDEX IF NOT EXISTS ix_audit_evidence_links_company_workpaper ON public.audit_evidence_links(company_id, workpaper_id);
        CREATE INDEX IF NOT EXISTS ix_audit_evidence_links_company_finding ON public.audit_evidence_links(company_id, finding_id);
        CREATE INDEX IF NOT EXISTS ix_audit_evidence_links_company_source ON public.audit_evidence_links(company_id, source_module, source_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.audit_evidence_links;
        DROP TABLE IF EXISTS public.audit_findings;
        DROP TABLE IF EXISTS public.audit_workpapers;
        """
    )
