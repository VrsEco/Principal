"""create process portal publications

Revision ID: 20260520_2300
Revises: 20260520_1700
Create Date: 2026-05-20 23:00:00
"""

from alembic import op


revision = "20260520_2300"
down_revision = "20260520_1700"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.process_portal_publications (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            process_id INTEGER NOT NULL REFERENCES public.processes(id),
            source_bpmn_diagram_id INTEGER REFERENCES public.process_bpmn_diagrams(id),
            publication_version INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(30) NOT NULL DEFAULT 'draft',
            visibility_scope VARCHAR(30) NOT NULL DEFAULT 'linked_process',
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL,
            summary TEXT,
            content_snapshot_json JSON NOT NULL,
            published_by_user_id INTEGER REFERENCES public.users(id),
            published_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publications_company_id ON public.process_portal_publications (company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publications_process_id ON public.process_portal_publications (process_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publications_source_bpmn_diagram_id ON public.process_portal_publications (source_bpmn_diagram_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_process_portal_publications_process_version "
        "ON public.process_portal_publications (company_id, process_id, publication_version)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.process_portal_publication_grants (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            publication_id INTEGER NOT NULL REFERENCES public.process_portal_publications(id) ON DELETE CASCADE,
            grant_scope VARCHAR(30) NOT NULL DEFAULT 'user',
            user_id INTEGER REFERENCES public.users(id),
            employee_id INTEGER REFERENCES public.employees(id),
            process_id INTEGER REFERENCES public.processes(id),
            process_routine_id INTEGER REFERENCES public.process_routines(id),
            bpmn_element_id VARCHAR(255),
            can_view BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publication_grants_company_id ON public.process_portal_publication_grants (company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publication_grants_publication_id ON public.process_portal_publication_grants (publication_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publication_grants_user_id ON public.process_portal_publication_grants (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publication_grants_employee_id ON public.process_portal_publication_grants (employee_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publication_grants_process_routine_id ON public.process_portal_publication_grants (process_routine_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_process_portal_publication_grants_bpmn_element_id ON public.process_portal_publication_grants (bpmn_element_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publication_grants_bpmn_element_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publication_grants_process_routine_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publication_grants_employee_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publication_grants_user_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publication_grants_publication_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publication_grants_company_id")
    op.execute("DROP TABLE IF EXISTS public.process_portal_publication_grants")

    op.execute("DROP INDEX IF EXISTS public.uq_process_portal_publications_process_version")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publications_source_bpmn_diagram_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publications_process_id")
    op.execute("DROP INDEX IF EXISTS public.ix_process_portal_publications_company_id")
    op.execute("DROP TABLE IF EXISTS public.process_portal_publications")
