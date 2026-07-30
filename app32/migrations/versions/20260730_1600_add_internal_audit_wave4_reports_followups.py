"""add internal audit wave4 reports and followups

Revision ID: 20260730_1600
Revises: 20260727_2100
Create Date: 2026-07-30 16:00:00
"""

from alembic import op


revision = "20260730_1600"
down_revision = "20260727_2100"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.audit_reports (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            execution_id INTEGER NOT NULL REFERENCES public.audit_executions(id) ON DELETE RESTRICT,
            version INTEGER NOT NULL DEFAULT 1,
            supersedes_report_id INTEGER REFERENCES public.audit_reports(id) ON DELETE SET NULL,
            title VARCHAR(255) NOT NULL,
            objective TEXT,
            scope_text TEXT,
            period_start DATE,
            period_end DATE,
            executive_summary TEXT,
            auditor_conclusion TEXT,
            opinion VARCHAR(80),
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            prepared_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            approved_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            approved_at TIMESTAMP WITHOUT TIME ZONE,
            issued_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_reports_status
                CHECK (status IN ('draft','issued','superseded','cancelled')),
            CONSTRAINT uq_audit_reports_company_execution_version
                UNIQUE (company_id, execution_id, version)
        );

        CREATE INDEX IF NOT EXISTS ix_audit_reports_company_status
            ON public.audit_reports (company_id, status);
        CREATE INDEX IF NOT EXISTS ix_audit_reports_company_execution
            ON public.audit_reports (company_id, execution_id);
        CREATE INDEX IF NOT EXISTS ix_audit_reports_company_issued
            ON public.audit_reports (company_id, issued_at);

        CREATE TABLE IF NOT EXISTS public.audit_follow_ups (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            finding_id INTEGER NOT NULL REFERENCES public.audit_findings(id) ON DELETE CASCADE,
            previous_status VARCHAR(40),
            status VARCHAR(40) NOT NULL DEFAULT 'awaiting_action',
            action_summary TEXT,
            auditor_notes TEXT,
            evidence_summary TEXT,
            due_date DATE,
            next_review_date DATE,
            performed_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_follow_ups_status
                CHECK (status IN ('awaiting_action','in_progress','awaiting_validation','resolved','closed','reopened'))
        );

        CREATE INDEX IF NOT EXISTS ix_audit_follow_ups_company_finding
            ON public.audit_follow_ups (company_id, finding_id);
        CREATE INDEX IF NOT EXISTS ix_audit_follow_ups_company_status
            ON public.audit_follow_ups (company_id, status);
        CREATE INDEX IF NOT EXISTS ix_audit_follow_ups_company_review
            ON public.audit_follow_ups (company_id, next_review_date);
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.audit_follow_ups CASCADE")
    op.execute("DROP TABLE IF EXISTS public.audit_reports CASCADE")
