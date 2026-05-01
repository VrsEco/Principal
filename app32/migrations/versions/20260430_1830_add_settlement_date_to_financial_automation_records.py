"""add settlement_date to financial automation records

Revision ID: 20260430_1830
Revises: 20260423_2200
Create Date: 2026-04-30 18:30:00
"""

from alembic import op


revision = "20260430_1830"
down_revision = "20260423_2200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.financial_automation_records
            ADD COLUMN IF NOT EXISTS settlement_date DATE;

        CREATE INDEX IF NOT EXISTS ix_financial_automation_records_settlement_date
            ON public.financial_automation_records (settlement_date);

        UPDATE public.financial_automation_records
           SET settlement_date = COALESCE(settlement_date, due_date, competence_date, issue_date)
         WHERE settlement_state = 'settled'
           AND settlement_date IS NULL;
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_financial_automation_records_settlement_date;
        ALTER TABLE public.financial_automation_records
            DROP COLUMN IF EXISTS settlement_date;
        """
    )
