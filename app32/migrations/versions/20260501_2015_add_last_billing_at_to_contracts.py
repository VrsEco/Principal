"""add last billing at to contracts

Revision ID: 20260501_2015
Revises: 20260501_1530
Create Date: 2026-05-01 20:15:00
"""

from alembic import op


revision = "20260501_2015"
down_revision = "20260501_1530"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.contracts
        ADD COLUMN IF NOT EXISTS last_billing_at DATE;
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE public.contracts
        DROP COLUMN IF EXISTS last_billing_at;
        """
    )
