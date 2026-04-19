"""add explicit competence_date to financial schedules

Revision ID: 20260419_1030
Revises: 20260417_1830
Create Date: 2026-04-19 10:30:00
"""

from alembic import op


revision = "20260419_1030"
down_revision = "20260417_1830"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.financial_schedules
            ADD COLUMN IF NOT EXISTS competence_date DATE;

        UPDATE public.financial_schedules
           SET competence_date = COALESCE(competence_date, start_date)
         WHERE competence_date IS NULL;

        ALTER TABLE public.financial_schedules
            ALTER COLUMN competence_date SET NOT NULL;

        CREATE INDEX IF NOT EXISTS ix_financial_schedules_competence_date
            ON public.financial_schedules (competence_date);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_financial_schedules_competence_date;

        ALTER TABLE public.financial_schedules
            DROP COLUMN IF EXISTS competence_date;
        """
    )
