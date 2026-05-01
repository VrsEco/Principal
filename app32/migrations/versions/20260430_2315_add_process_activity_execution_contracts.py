"""add process activity execution contracts

Revision ID: 20260430_2315
Revises: 20260430_2230
Create Date: 2026-04-30 23:15:00
"""

from alembic import op


revision = "20260430_2315"
down_revision = "20260430_2230"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.process_activity_execution_contracts (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_id INTEGER NOT NULL REFERENCES public.processes(id) ON DELETE CASCADE,
            process_routine_id INTEGER REFERENCES public.process_routines(id) ON DELETE CASCADE,
            bpmn_element_id VARCHAR(255),
            version INTEGER NOT NULL DEFAULT 1,
            execution_mode VARCHAR(50) NOT NULL DEFAULT 'manual_external',
            interaction_mode VARCHAR(50),
            capability_key VARCHAR(120),
            route_name VARCHAR(255),
            ui_schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            rest_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            mcp_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            auto_service_key VARCHAR(120),
            requires_human_gate BOOLEAN NOT NULL DEFAULT FALSE,
            allows_pause BOOLEAN NOT NULL DEFAULT TRUE,
            allows_retry BOOLEAN NOT NULL DEFAULT TRUE,
            sla_minutes INTEGER,
            completion_rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_process_activity_execution_contracts_lookup
            ON public.process_activity_execution_contracts (company_id, process_id, bpmn_element_id, is_active);
        CREATE INDEX IF NOT EXISTS ix_process_activity_execution_contracts_routine
            ON public.process_activity_execution_contracts (process_routine_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_process_activity_execution_contracts_routine;
        DROP INDEX IF EXISTS public.ix_process_activity_execution_contracts_lookup;
        DROP TABLE IF EXISTS public.process_activity_execution_contracts;
        """
    )
