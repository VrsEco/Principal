"""add explicit financial schedule link to entries

Revision ID: 20260419_1600
Revises: 20260419_1500
Create Date: 2026-04-19 16:00:00
"""

from alembic import op


revision = "20260419_1600"
down_revision = "20260419_1500"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.financial_entries
            ADD COLUMN IF NOT EXISTS financial_schedule_id INTEGER;

        UPDATE public.financial_entries AS entry
           SET financial_schedule_id = schedule.id,
               updated_at = NOW()
          FROM public.financial_schedules AS schedule
         WHERE entry.company_id = schedule.company_id
           AND entry.external_reference = ('financial_schedule:' || schedule.id::text)
           AND entry.deleted_at IS NULL
           AND schedule.deleted_at IS NULL
           AND entry.financial_schedule_id IS NULL;

        CREATE INDEX IF NOT EXISTS ix_financial_entries_financial_schedule_id
            ON public.financial_entries (financial_schedule_id);

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM pg_constraint
                 WHERE conname = 'fk_financial_entries_financial_schedule_id'
            ) THEN
                ALTER TABLE public.financial_entries
                    ADD CONSTRAINT fk_financial_entries_financial_schedule_id
                    FOREIGN KEY (financial_schedule_id)
                    REFERENCES public.financial_schedules(id)
                    ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE public.financial_entries
            DROP CONSTRAINT IF EXISTS fk_financial_entries_financial_schedule_id;

        DROP INDEX IF EXISTS public.ix_financial_entries_financial_schedule_id;

        ALTER TABLE public.financial_entries
            DROP COLUMN IF EXISTS financial_schedule_id;
        """
    )
