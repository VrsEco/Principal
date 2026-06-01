"""create_instruction_registry_tables

Revision ID: 20260517_1200
Revises: 20260507_1100
Create Date: 2026-05-17 12:00:00.000000
"""

from alembic import op


revision = "20260517_1200"
down_revision = "20260507_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.instruction_registry_entries (
            id SERIAL PRIMARY KEY,
            scope_type VARCHAR(24) NOT NULL,
            runtime_profile VARCHAR(80) NOT NULL,
            agent_key VARCHAR(80),
            harness_key VARCHAR(120),
            company_id INTEGER REFERENCES public.companies(id) ON DELETE CASCADE,
            channel VARCHAR(20) NOT NULL,
            environment VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            rollout_status VARCHAR(30) NOT NULL,
            entry_version VARCHAR(40) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            invalidation_token VARCHAR(64) NOT NULL,
            cache_ttl_seconds INTEGER NOT NULL,
            payload_json JSON NOT NULL,
            notes TEXT,
            last_invalidated_at TIMESTAMP,
            approved_by_user_id INTEGER REFERENCES public.users(id),
            approved_at TIMESTAMP,
            created_by_user_id INTEGER REFERENCES public.users(id),
            updated_by_user_id INTEGER REFERENCES public.users(id),
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_scope_type ON public.instruction_registry_entries (scope_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_runtime_profile ON public.instruction_registry_entries (runtime_profile)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_agent_key ON public.instruction_registry_entries (agent_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_harness_key ON public.instruction_registry_entries (harness_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_company_id ON public.instruction_registry_entries (company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_channel ON public.instruction_registry_entries (channel)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_environment ON public.instruction_registry_entries (environment)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_status ON public.instruction_registry_entries (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_entries_rollout_status ON public.instruction_registry_entries (rollout_status)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.instruction_registry_audit_logs (
            id SERIAL PRIMARY KEY,
            entry_id INTEGER REFERENCES public.instruction_registry_entries(id) ON DELETE SET NULL,
            company_id INTEGER REFERENCES public.companies(id) ON DELETE SET NULL,
            actor_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            event_type VARCHAR(60) NOT NULL,
            result VARCHAR(20) NOT NULL,
            detail TEXT,
            payload_json JSON NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_audit_logs_entry_id ON public.instruction_registry_audit_logs (entry_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_audit_logs_company_id ON public.instruction_registry_audit_logs (company_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_audit_logs_actor_user_id ON public.instruction_registry_audit_logs (actor_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_audit_logs_event_type ON public.instruction_registry_audit_logs (event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_audit_logs_result ON public.instruction_registry_audit_logs (result)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_instruction_registry_audit_logs_created_at ON public.instruction_registry_audit_logs (created_at)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_audit_logs_created_at")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_audit_logs_result")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_audit_logs_event_type")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_audit_logs_actor_user_id")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_audit_logs_company_id")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_audit_logs_entry_id")
    op.execute("DROP TABLE IF EXISTS public.instruction_registry_audit_logs")

    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_rollout_status")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_status")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_environment")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_channel")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_company_id")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_harness_key")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_agent_key")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_runtime_profile")
    op.execute("DROP INDEX IF EXISTS public.ix_instruction_registry_entries_scope_type")
    op.execute("DROP TABLE IF EXISTS public.instruction_registry_entries")
