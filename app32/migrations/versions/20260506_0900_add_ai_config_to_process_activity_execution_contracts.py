"""add ai config to process activity execution contracts

Revision ID: 20260506_0900
Revises: 20260501_1200
Create Date: 2026-05-06 09:00:00
"""

from alembic import op


revision = "20260506_0900"
down_revision = "20260501_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.process_activity_execution_contracts
            ADD COLUMN IF NOT EXISTS ai_config_json JSONB NOT NULL DEFAULT '{}'::jsonb;
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE public.process_activity_execution_contracts
            DROP COLUMN IF EXISTS ai_config_json;
        """
    )
