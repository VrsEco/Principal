"""add internal audit wave2 execution points

Revision ID: 20260719_0900
Revises: 20260718_1200
Create Date: 2026-07-19 09:00:00
"""

from alembic import op


revision = "20260719_0900"
down_revision = "20260718_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.audit_points (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            origin_type VARCHAR(30) NOT NULL DEFAULT 'manual',
            source_module VARCHAR(60) NOT NULL DEFAULT 'audit',
            subject_type VARCHAR(80),
            subject_id INTEGER,
            severity VARCHAR(30) NOT NULL DEFAULT 'medium',
            status VARCHAR(40) NOT NULL DEFAULT 'open',
            assigned_to_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            detected_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            due_date DATE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_points_origin_type CHECK (origin_type IN ('manual','checklist','analyzer')),
            CONSTRAINT ck_audit_points_severity CHECK (severity IN ('low','medium','high','critical')),
            CONSTRAINT ck_audit_points_status CHECK (status IN ('open','in_review','converted_to_finding','dismissed','closed'))
        );
        CREATE INDEX IF NOT EXISTS ix_audit_points_company_id ON public.audit_points(company_id);
        CREATE INDEX IF NOT EXISTS ix_audit_points_company_status ON public.audit_points(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_audit_points_company_severity ON public.audit_points(company_id, severity);
        CREATE INDEX IF NOT EXISTS ix_audit_points_company_due_date ON public.audit_points(company_id, due_date);

        CREATE TABLE IF NOT EXISTS public.audit_executions (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            checklist_id INTEGER NOT NULL REFERENCES public.audit_checklists(id) ON DELETE CASCADE,
            schedule_id INTEGER REFERENCES public.audit_schedules(id) ON DELETE SET NULL,
            area_id INTEGER REFERENCES public.audit_areas(id) ON DELETE SET NULL,
            auditor_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            period_label VARCHAR(120),
            planned_start_date DATE,
            planned_end_date DATE,
            started_at TIMESTAMP WITHOUT TIME ZONE,
            completed_at TIMESTAMP WITHOUT TIME ZONE,
            status VARCHAR(30) NOT NULL DEFAULT 'planned',
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_executions_status CHECK (status IN ('planned','in_progress','completed','cancelled'))
        );
        CREATE INDEX IF NOT EXISTS ix_audit_executions_company_id ON public.audit_executions(company_id);
        CREATE INDEX IF NOT EXISTS ix_audit_executions_company_status ON public.audit_executions(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_audit_executions_company_checklist ON public.audit_executions(company_id, checklist_id);
        CREATE INDEX IF NOT EXISTS ix_audit_executions_company_schedule ON public.audit_executions(company_id, schedule_id);

        CREATE TABLE IF NOT EXISTS public.audit_execution_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            execution_id INTEGER NOT NULL REFERENCES public.audit_executions(id) ON DELETE CASCADE,
            checklist_item_id INTEGER NOT NULL REFERENCES public.audit_checklist_items(id) ON DELETE CASCADE,
            status VARCHAR(40) NOT NULL DEFAULT 'not_tested',
            justification TEXT,
            comments TEXT,
            audit_point_id INTEGER REFERENCES public.audit_points(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_execution_items_status CHECK (status IN ('conforming','qualified_conforming','non_conforming','not_applicable','not_tested')),
            CONSTRAINT uq_audit_execution_items_execution_item UNIQUE(company_id, execution_id, checklist_item_id)
        );
        CREATE INDEX IF NOT EXISTS ix_audit_execution_items_company_id ON public.audit_execution_items(company_id);
        CREATE INDEX IF NOT EXISTS ix_audit_execution_items_company_execution ON public.audit_execution_items(company_id, execution_id);
        CREATE INDEX IF NOT EXISTS ix_audit_execution_items_company_status ON public.audit_execution_items(company_id, status);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.audit_execution_items;
        DROP TABLE IF EXISTS public.audit_executions;
        DROP TABLE IF EXISTS public.audit_points;
        """
    )
