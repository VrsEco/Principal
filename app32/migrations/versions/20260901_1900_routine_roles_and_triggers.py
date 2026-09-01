"""Adiciona funções e gatilhos às regras de execução das rotinas.

Revision ID: 20260901_1900
Revises: 20260826_2000
Create Date: 2026-09-01 19:00:00
"""

from alembic import op


revision = "20260901_1900"
down_revision = "20260826_2000"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE routines
            ADD COLUMN IF NOT EXISTS execution_mode VARCHAR(20) NOT NULL DEFAULT 'scheduled';

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_routines_execution_mode'
            ) THEN
                ALTER TABLE routines
                    ADD CONSTRAINT ck_routines_execution_mode
                    CHECK (execution_mode IN ('scheduled', 'triggered', 'hybrid'));
            END IF;
        END $$;

        CREATE TABLE IF NOT EXISTS routine_role_assignments (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            routine_id INTEGER NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            assignment_type VARCHAR(20) NOT NULL,
            distribution_mode VARCHAR(20) NOT NULL DEFAULT 'collective',
            hours_used NUMERIC(10, 2) NOT NULL DEFAULT 0,
            notes TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_routine_role_assignment
                UNIQUE (company_id, routine_id, role_id, assignment_type),
            CONSTRAINT ck_routine_role_assignment_type
                CHECK (assignment_type IN ('responsible', 'executor')),
            CONSTRAINT ck_routine_role_distribution
                CHECK (distribution_mode IN ('collective', 'individual', 'pool')),
            CONSTRAINT ck_routine_role_hours_nonnegative
                CHECK (hours_used >= 0)
        );

        CREATE INDEX IF NOT EXISTS ix_routine_role_assignments_company_id
            ON routine_role_assignments(company_id);
        CREATE INDEX IF NOT EXISTS ix_routine_role_assignments_routine_id
            ON routine_role_assignments(routine_id);
        CREATE INDEX IF NOT EXISTS ix_routine_role_assignments_role_id
            ON routine_role_assignments(role_id);

        CREATE UNIQUE INDEX IF NOT EXISTS uq_routine_single_responsible_role
            ON routine_role_assignments(company_id, routine_id)
            WHERE assignment_type = 'responsible' AND is_active = TRUE;

        CREATE TABLE IF NOT EXISTS routine_triggers (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            routine_id INTEGER NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
            trigger_type VARCHAR(20) NOT NULL DEFAULT 'event',
            trigger_code VARCHAR(100) NOT NULL,
            name VARCHAR(160) NOT NULL,
            activation_policy VARCHAR(20) NOT NULL DEFAULT 'automatic',
            config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_routine_trigger_code
                UNIQUE (company_id, routine_id, trigger_code),
            CONSTRAINT ck_routine_trigger_type
                CHECK (trigger_type IN ('event', 'manual')),
            CONSTRAINT ck_routine_trigger_activation
                CHECK (activation_policy IN ('automatic', 'confirmation'))
        );

        CREATE INDEX IF NOT EXISTS ix_routine_triggers_company_id
            ON routine_triggers(company_id);
        CREATE INDEX IF NOT EXISTS ix_routine_triggers_routine_id
            ON routine_triggers(routine_id);
        CREATE INDEX IF NOT EXISTS ix_routine_triggers_code
            ON routine_triggers(company_id, trigger_code);

        CREATE TABLE IF NOT EXISTS routine_trigger_events (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            routine_id INTEGER NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
            trigger_id INTEGER NOT NULL REFERENCES routine_triggers(id) ON DELETE CASCADE,
            event_key VARCHAR(200) NOT NULL,
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(30) NOT NULL DEFAULT 'received',
            created_instances_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            processed_at TIMESTAMP WITHOUT TIME ZONE,
            CONSTRAINT uq_routine_trigger_event_key
                UNIQUE (company_id, trigger_id, event_key),
            CONSTRAINT ck_routine_trigger_event_status
                CHECK (status IN ('received', 'pending_confirmation', 'processed', 'failed', 'ignored'))
        );

        CREATE INDEX IF NOT EXISTS ix_routine_trigger_events_company_id
            ON routine_trigger_events(company_id);
        CREATE INDEX IF NOT EXISTS ix_routine_trigger_events_routine_id
            ON routine_trigger_events(routine_id);
        CREATE INDEX IF NOT EXISTS ix_routine_trigger_events_trigger_id
            ON routine_trigger_events(trigger_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS routine_trigger_events;
        DROP TABLE IF EXISTS routine_triggers;
        DROP TABLE IF EXISTS routine_role_assignments;
        ALTER TABLE routines DROP CONSTRAINT IF EXISTS ck_routines_execution_mode;
        ALTER TABLE routines DROP COLUMN IF EXISTS execution_mode;
        """
    )
