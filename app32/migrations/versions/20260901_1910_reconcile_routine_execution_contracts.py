"""Reconcile constraints skipped when routine execution tables pre-existed."""

from alembic import op


revision = "20260901_1910"
down_revision = "20260901_1900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_routine_role_assignment_type') THEN
            ALTER TABLE routine_role_assignments ADD CONSTRAINT ck_routine_role_assignment_type CHECK (assignment_type IN ('responsible','executor'));
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_routine_role_distribution') THEN
            ALTER TABLE routine_role_assignments ADD CONSTRAINT ck_routine_role_distribution CHECK (distribution_mode IN ('collective','individual','pool'));
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_routine_role_hours_nonnegative') THEN
            ALTER TABLE routine_role_assignments ADD CONSTRAINT ck_routine_role_hours_nonnegative CHECK (hours_used >= 0);
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_routine_trigger_type') THEN
            ALTER TABLE routine_triggers ADD CONSTRAINT ck_routine_trigger_type CHECK (trigger_type IN ('event','manual'));
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_routine_trigger_activation') THEN
            ALTER TABLE routine_triggers ADD CONSTRAINT ck_routine_trigger_activation CHECK (activation_policy IN ('automatic','confirmation'));
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ck_routine_trigger_event_status') THEN
            ALTER TABLE routine_trigger_events ADD CONSTRAINT ck_routine_trigger_event_status CHECK (status IN ('received','pending_confirmation','processed','failed','ignored'));
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    pass
