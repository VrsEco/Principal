"""Add conversion_requested status to assisted analyses.

Revision ID: 20260702_1800
Revises: 20260701_1045
Create Date: 2026-07-02
"""

from alembic import op


revision = "20260702_1800"
down_revision = "20260701_1045"
branch_labels = None
depends_on = None


STATUS_VALUES = (
    "'received'",
    "'under_review'",
    "'validated'",
    "'rejected'",
    "'conversion_requested'",
    "'converted'",
    "'archived'",
)


def upgrade() -> None:
    allowed = ", ".join(STATUS_VALUES)
    op.execute(
        f"""
        ALTER TABLE public.consultive_assisted_analyses
            DROP CONSTRAINT IF EXISTS ck_consultive_assisted_analyses_status;
        ALTER TABLE public.consultive_assisted_analyses
            ADD CONSTRAINT ck_consultive_assisted_analyses_status
            CHECK (status IN ({allowed}));
        """
    )


def downgrade() -> None:
    legacy_allowed = ", ".join(value for value in STATUS_VALUES if value != "'conversion_requested'")
    op.execute(
        """
        UPDATE public.consultive_assisted_analyses
        SET status = 'under_review'
        WHERE status = 'conversion_requested';
        """
    )
    op.execute(
        f"""
        ALTER TABLE public.consultive_assisted_analyses
            DROP CONSTRAINT IF EXISTS ck_consultive_assisted_analyses_status;
        ALTER TABLE public.consultive_assisted_analyses
            ADD CONSTRAINT ck_consultive_assisted_analyses_status
            CHECK (status IN ({legacy_allowed}));
        """
    )
