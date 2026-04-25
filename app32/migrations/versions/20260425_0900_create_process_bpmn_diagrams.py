"""create process BPMN diagrams

Revision ID: 20260425_0900
Revises: 20260423_2200
Create Date: 2026-04-25 09:00:00
"""

from alembic import op


revision = "20260425_0900"
down_revision = "20260423_2200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.process_bpmn_diagrams (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_id INTEGER NOT NULL REFERENCES public.processes(id) ON DELETE CASCADE,
            version INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            name VARCHAR(255),
            bpmn_xml TEXT NOT NULL,
            svg_snapshot TEXT,
            png_snapshot TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            published_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_process_bpmn_diagrams_company_id
            ON public.process_bpmn_diagrams (company_id);
        CREATE INDEX IF NOT EXISTS ix_process_bpmn_diagrams_process_id
            ON public.process_bpmn_diagrams (process_id);
        CREATE INDEX IF NOT EXISTS ix_process_bpmn_diagrams_company_process_status
            ON public.process_bpmn_diagrams (company_id, process_id, status);
        CREATE INDEX IF NOT EXISTS ix_process_bpmn_diagrams_company_process_version
            ON public.process_bpmn_diagrams (company_id, process_id, version DESC);
        CREATE INDEX IF NOT EXISTS ix_process_bpmn_diagrams_updated_at
            ON public.process_bpmn_diagrams (updated_at DESC);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_process_bpmn_diagrams_updated_at;
        DROP INDEX IF EXISTS public.ix_process_bpmn_diagrams_company_process_version;
        DROP INDEX IF EXISTS public.ix_process_bpmn_diagrams_company_process_status;
        DROP INDEX IF EXISTS public.ix_process_bpmn_diagrams_process_id;
        DROP INDEX IF EXISTS public.ix_process_bpmn_diagrams_company_id;
        DROP TABLE IF EXISTS public.process_bpmn_diagrams;
        """
    )
