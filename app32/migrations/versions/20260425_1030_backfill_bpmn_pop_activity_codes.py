"""backfill BPMN POP activity business codes

Revision ID: 20260425_1030
Revises: 20260425_1010
Create Date: 2026-04-25 10:30:00
"""

from alembic import op


revision = "20260425_1030"
down_revision = "20260425_1010"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        r"""
        WITH candidates AS (
            SELECT
                pr.id,
                matched.parts[1] AS business_code,
                btrim(matched.parts[2]) AS business_name
            FROM public.process_routines pr
            JOIN public.processes p
              ON p.id = pr.process_id
             AND p.company_id = pr.company_id
            CROSS JOIN LATERAL (
                SELECT regexp_match(
                    COALESCE(pr.name, ''),
                    '^([A-Z]{1,6}(?:\.[A-Z0-9]+)+\.[0-9]{2})[[:space:]]*[-–—:][[:space:]]*(.+)$'
                ) AS parts
            ) AS matched
            WHERE matched.parts IS NOT NULL
              AND (
                    pr.code IS NULL
                 OR btrim(pr.code) = ''
                 OR pr.code = pr.bpmn_element_id
                 OR pr.code ~ '^(Activity|Task|SubProcess|CallActivity)_[A-Za-z0-9]+$'
              )
        )
        UPDATE public.process_routines pr
           SET code = candidates.business_code,
               name = candidates.business_name
          FROM candidates
         WHERE pr.id = candidates.id
           AND candidates.business_code IS NOT NULL
           AND candidates.business_name IS NOT NULL
           AND btrim(candidates.business_name) <> '';
        """
    )


def downgrade():
    # Data backfill intentionally not reversible.
    pass
