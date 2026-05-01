"""add process instance runtime base

Revision ID: 20260430_2230
Revises: 20260430_2100
Create Date: 2026-04-30 22:30:00
"""

from alembic import op


revision = "20260430_2230"
down_revision = "20260430_2100"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.process_instances
            ADD COLUMN IF NOT EXISTS process_bpmn_diagram_id INTEGER REFERENCES public.process_bpmn_diagrams(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS process_version INTEGER,
            ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP WITHOUT TIME ZONE,
            ADD COLUMN IF NOT EXISTS pause_reason TEXT,
            ADD COLUMN IF NOT EXISTS current_bpmn_element_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS runtime_context_json JSONB NOT NULL DEFAULT '{}'::jsonb;

        CREATE INDEX IF NOT EXISTS ix_process_instances_bpmn_runtime
            ON public.process_instances (company_id, process_id, status, current_bpmn_element_id);

        CREATE TABLE IF NOT EXISTS public.process_instance_executions (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_instance_id INTEGER NOT NULL REFERENCES public.process_instances(id) ON DELETE CASCADE,
            process_id INTEGER NOT NULL REFERENCES public.processes(id) ON DELETE CASCADE,
            process_bpmn_diagram_id INTEGER REFERENCES public.process_bpmn_diagrams(id) ON DELETE SET NULL,
            bpmn_element_id VARCHAR(255) NOT NULL,
            bpmn_element_name VARCHAR(255),
            bpmn_element_type VARCHAR(80),
            execution_mode VARCHAR(50) NOT NULL DEFAULT 'human_task',
            interaction_mode VARCHAR(50),
            handler_key VARCHAR(120),
            capability_key VARCHAR(120),
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            started_at TIMESTAMP WITHOUT TIME ZONE,
            completed_at TIMESTAMP WITHOUT TIME ZONE,
            paused_at TIMESTAMP WITHOUT TIME ZONE,
            waiting_since TIMESTAMP WITHOUT TIME ZONE,
            duration_seconds INTEGER,
            estimated_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
            actual_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
            performed_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            performer_type VARCHAR(50),
            external_ref VARCHAR(255),
            request_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            response_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            error_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_process_instance_executions_instance
            ON public.process_instance_executions (company_id, process_instance_id, status);
        CREATE INDEX IF NOT EXISTS ix_process_instance_executions_bpmn_element
            ON public.process_instance_executions (company_id, process_id, bpmn_element_id);
        CREATE INDEX IF NOT EXISTS ix_process_instance_executions_created_at
            ON public.process_instance_executions (created_at DESC);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_process_instance_executions_created_at;
        DROP INDEX IF EXISTS public.ix_process_instance_executions_bpmn_element;
        DROP INDEX IF EXISTS public.ix_process_instance_executions_instance;
        DROP TABLE IF EXISTS public.process_instance_executions;

        DROP INDEX IF EXISTS public.ix_process_instances_bpmn_runtime;

        ALTER TABLE public.process_instances
            DROP COLUMN IF EXISTS runtime_context_json,
            DROP COLUMN IF EXISTS current_bpmn_element_id,
            DROP COLUMN IF EXISTS pause_reason,
            DROP COLUMN IF EXISTS paused_at,
            DROP COLUMN IF EXISTS process_version,
            DROP COLUMN IF EXISTS process_bpmn_diagram_id;
        """
    )
