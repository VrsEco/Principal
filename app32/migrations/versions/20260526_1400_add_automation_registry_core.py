"""add automation registry core

Revision ID: 20260526_1400
Revises: 20260526_1230
Create Date: 2026-05-26 14:00:00
"""

from alembic import op


revision = "20260526_1400"
down_revision = "20260526_1230"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.automation_registry (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            name VARCHAR(150) NOT NULL,
            module_key VARCHAR(50) NOT NULL,
            origin_type VARCHAR(30) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            entity_id INTEGER NOT NULL,
            trigger_type VARCHAR(30) NOT NULL,
            action_type VARCHAR(50) NOT NULL,
            execution_mode VARCHAR(30) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'active',
            requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            next_execution_at TIMESTAMP WITHOUT TIME ZONE,
            last_execution_at TIMESTAMP WITHOUT TIME ZONE,
            last_result VARCHAR(30),
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_automation_registry_company ON public.automation_registry(company_id);
        CREATE INDEX IF NOT EXISTS ix_automation_registry_module ON public.automation_registry(company_id, module_key);
        CREATE INDEX IF NOT EXISTS ix_automation_registry_entity ON public.automation_registry(company_id, entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS ix_automation_registry_status ON public.automation_registry(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_automation_registry_next_exec ON public.automation_registry(company_id, next_execution_at);

        CREATE TABLE IF NOT EXISTS public.automation_rule (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            automation_registry_id INTEGER NOT NULL REFERENCES public.automation_registry(id) ON DELETE CASCADE,
            rule_code VARCHAR(80) NOT NULL,
            trigger_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            action_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            policy_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_automation_rule_registry UNIQUE(company_id, automation_registry_id)
        );
        CREATE INDEX IF NOT EXISTS ix_automation_rule_company ON public.automation_rule(company_id);
        CREATE INDEX IF NOT EXISTS ix_automation_rule_code ON public.automation_rule(company_id, rule_code);

        CREATE TABLE IF NOT EXISTS public.automation_execution (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            automation_registry_id INTEGER NOT NULL REFERENCES public.automation_registry(id) ON DELETE CASCADE,
            execution_key VARCHAR(160) NOT NULL,
            trigger_event VARCHAR(60),
            triggered_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            started_at TIMESTAMP WITHOUT TIME ZONE,
            finished_at TIMESTAMP WITHOUT TIME ZONE,
            status VARCHAR(30) NOT NULL,
            result_message TEXT,
            entity_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            execution_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            error_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            reversed_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_automation_execution_key UNIQUE(company_id, execution_key)
        );
        CREATE INDEX IF NOT EXISTS ix_automation_execution_company ON public.automation_execution(company_id);
        CREATE INDEX IF NOT EXISTS ix_automation_execution_registry ON public.automation_execution(company_id, automation_registry_id);
        CREATE INDEX IF NOT EXISTS ix_automation_execution_status ON public.automation_execution(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_automation_execution_triggered ON public.automation_execution(company_id, triggered_at);

        CREATE TABLE IF NOT EXISTS public.automation_bpms_link (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            automation_registry_id INTEGER NOT NULL REFERENCES public.automation_registry(id) ON DELETE CASCADE,
            process_id INTEGER REFERENCES public.processes(id) ON DELETE SET NULL,
            process_step_id INTEGER REFERENCES public.process_steps(id) ON DELETE SET NULL,
            process_instance_id INTEGER REFERENCES public.process_instances(id) ON DELETE SET NULL,
            bpms_mode VARCHAR(30),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_automation_bpms_link_company ON public.automation_bpms_link(company_id);
        CREATE INDEX IF NOT EXISTS ix_automation_bpms_link_registry ON public.automation_bpms_link(company_id, automation_registry_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_automation_bpms_link_registry;
        DROP INDEX IF EXISTS public.ix_automation_bpms_link_company;
        DROP TABLE IF EXISTS public.automation_bpms_link;

        DROP INDEX IF EXISTS public.ix_automation_execution_triggered;
        DROP INDEX IF EXISTS public.ix_automation_execution_status;
        DROP INDEX IF EXISTS public.ix_automation_execution_registry;
        DROP INDEX IF EXISTS public.ix_automation_execution_company;
        DROP TABLE IF EXISTS public.automation_execution;

        DROP INDEX IF EXISTS public.ix_automation_rule_code;
        DROP INDEX IF EXISTS public.ix_automation_rule_company;
        DROP TABLE IF EXISTS public.automation_rule;

        DROP INDEX IF EXISTS public.ix_automation_registry_next_exec;
        DROP INDEX IF EXISTS public.ix_automation_registry_status;
        DROP INDEX IF EXISTS public.ix_automation_registry_entity;
        DROP INDEX IF EXISTS public.ix_automation_registry_module;
        DROP INDEX IF EXISTS public.ix_automation_registry_company;
        DROP TABLE IF EXISTS public.automation_registry;
        """
    )
