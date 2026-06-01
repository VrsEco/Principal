"""create internal audit phase 01 base

Revision ID: 20260531_1800
Revises: 20260531_1400
Create Date: 2026-05-31 18:00:00
"""

from alembic import op


revision = "20260531_1800"
down_revision = "20260531_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.audit_areas (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            name VARCHAR(180) NOT NULL,
            description TEXT,
            manager_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_audit_areas_company_name UNIQUE(company_id, name)
        );
        CREATE INDEX IF NOT EXISTS ix_audit_areas_company_active ON public.audit_areas(company_id, active);
        CREATE INDEX IF NOT EXISTS ix_audit_areas_company_id ON public.audit_areas(company_id);

        CREATE TABLE IF NOT EXISTS public.audit_auditors (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            employee_id INTEGER REFERENCES public.employees(id) ON DELETE SET NULL,
            role VARCHAR(40) NOT NULL DEFAULT 'auditor',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_audit_auditors_company_user UNIQUE(company_id, user_id),
            CONSTRAINT ck_audit_auditors_role CHECK (role IN ('auditor_admin','auditor','viewer_executivo'))
        );
        CREATE INDEX IF NOT EXISTS ix_audit_auditors_company_active ON public.audit_auditors(company_id, active);
        CREATE INDEX IF NOT EXISTS ix_audit_auditors_company_role ON public.audit_auditors(company_id, role);
        CREATE INDEX IF NOT EXISTS ix_audit_auditors_company_id ON public.audit_auditors(company_id);

        CREATE TABLE IF NOT EXISTS public.audit_checklists (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            checklist_type VARCHAR(30) NOT NULL DEFAULT 'autonomous',
            linked_process_id INTEGER REFERENCES public.processes(id) ON DELETE SET NULL,
            linked_project_id INTEGER REFERENCES public.projects(id) ON DELETE SET NULL,
            linked_routine_id INTEGER REFERENCES public.routines(id) ON DELETE SET NULL,
            area_id INTEGER REFERENCES public.audit_areas(id) ON DELETE SET NULL,
            owner_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            default_periodicity VARCHAR(60),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_checklists_type CHECK (checklist_type IN ('process','project','autonomous'))
        );
        CREATE INDEX IF NOT EXISTS ix_audit_checklists_company_active ON public.audit_checklists(company_id, active);
        CREATE INDEX IF NOT EXISTS ix_audit_checklists_company_type ON public.audit_checklists(company_id, checklist_type);
        CREATE INDEX IF NOT EXISTS ix_audit_checklists_company_area ON public.audit_checklists(company_id, area_id);
        CREATE INDEX IF NOT EXISTS ix_audit_checklists_company_id ON public.audit_checklists(company_id);

        CREATE TABLE IF NOT EXISTS public.audit_checklist_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            checklist_id INTEGER NOT NULL REFERENCES public.audit_checklists(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            description_for_report TEXT NOT NULL,
            expected_evidence TEXT,
            criterion TEXT,
            weight NUMERIC(8, 2),
            sort_order INTEGER NOT NULL DEFAULT 100,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_audit_checklist_items_company_checklist ON public.audit_checklist_items(company_id, checklist_id);
        CREATE INDEX IF NOT EXISTS ix_audit_checklist_items_company_active ON public.audit_checklist_items(company_id, active);
        CREATE INDEX IF NOT EXISTS ix_audit_checklist_items_company_id ON public.audit_checklist_items(company_id);

        CREATE TABLE IF NOT EXISTS public.audit_schedules (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            process_id INTEGER REFERENCES public.processes(id) ON DELETE SET NULL,
            routine_id INTEGER REFERENCES public.routines(id) ON DELETE SET NULL,
            checklist_id INTEGER REFERENCES public.audit_checklists(id) ON DELETE SET NULL,
            area_id INTEGER REFERENCES public.audit_areas(id) ON DELETE SET NULL,
            auditor_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            planned_start_date DATE,
            planned_end_date DATE,
            recurrence_rule VARCHAR(255),
            status VARCHAR(30) NOT NULL DEFAULT 'active',
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_audit_schedules_status CHECK (status IN ('active','paused','completed','cancelled'))
        );
        CREATE INDEX IF NOT EXISTS ix_audit_schedules_company_status ON public.audit_schedules(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_audit_schedules_company_checklist ON public.audit_schedules(company_id, checklist_id);
        CREATE INDEX IF NOT EXISTS ix_audit_schedules_company_id ON public.audit_schedules(company_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.audit_schedules;
        DROP TABLE IF EXISTS public.audit_checklist_items;
        DROP TABLE IF EXISTS public.audit_checklists;
        DROP TABLE IF EXISTS public.audit_auditors;
        DROP TABLE IF EXISTS public.audit_areas;
        """
    )
