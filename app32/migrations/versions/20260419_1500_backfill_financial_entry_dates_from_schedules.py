"""backfill financial entry dates from linked schedules

Revision ID: 20260419_1500
Revises: 20260419_1030
Create Date: 2026-04-19 15:00:00
"""

from alembic import op


revision = "20260419_1500"
down_revision = "20260419_1030"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE public.financial_entries AS entry
           SET competence_date = schedule.competence_date,
               due_date = COALESCE(entry.due_date, schedule.next_due_date, schedule.first_due_date, schedule.start_date),
               updated_at = NOW()
          FROM public.financial_schedules AS schedule
         WHERE entry.company_id = schedule.company_id
           AND entry.external_reference = ('financial_schedule:' || schedule.id::text)
           AND entry.deleted_at IS NULL
           AND schedule.deleted_at IS NULL
           AND schedule.competence_date IS NOT NULL
           AND entry.competence_date IS DISTINCT FROM schedule.competence_date;
        """
    )


def downgrade():
    # Data backfill only. There is no safe generic way to restore the previous
    # entry competence dates after correcting them from their source title.
    pass
