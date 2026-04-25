"""add BPMN binding fields to process routines

Revision ID: 20260425_1010
Revises: 20260425_0900
Create Date: 2026-04-25 10:10:00
"""

from alembic import op


revision = "20260425_1010"
down_revision = "20260425_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.process_routines
            ADD COLUMN IF NOT EXISTS bpmn_element_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS bpmn_element_type VARCHAR(80),
            ADD COLUMN IF NOT EXISTS bpmn_data_objects JSONB;

        CREATE INDEX IF NOT EXISTS ix_process_routines_bpmn_binding
            ON public.process_routines (company_id, process_id, bpmn_element_id)
            WHERE bpmn_element_id IS NOT NULL;
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_process_routines_bpmn_binding;
        ALTER TABLE public.process_routines
            DROP COLUMN IF EXISTS bpmn_data_objects,
            DROP COLUMN IF EXISTS bpmn_element_type,
            DROP COLUMN IF EXISTS bpmn_element_id;
        """
    )
