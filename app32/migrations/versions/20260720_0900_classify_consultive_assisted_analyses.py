"""classify consultive assisted analyses

Revision ID: 20260720_0900
Revises: 20260719_1030
Create Date: 2026-07-20 09:00:00
"""

from alembic import op

revision = "20260720_0900"
down_revision = "20260719_1030"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.consultive_assisted_analyses
            ADD COLUMN IF NOT EXISTS analysis_type VARCHAR(30) NOT NULL DEFAULT 'methodological',
            ADD COLUMN IF NOT EXISTS journey_eligible BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS eligibility_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb;

        ALTER TABLE public.consultive_assisted_analyses
            DROP CONSTRAINT IF EXISTS ck_consultive_assisted_analyses_analysis_type;
        ALTER TABLE public.consultive_assisted_analyses
            ADD CONSTRAINT ck_consultive_assisted_analyses_analysis_type
            CHECK (analysis_type IN ('methodological', 'technical_test'));

        UPDATE public.consultive_assisted_analyses
           SET analysis_type = 'technical_test',
               journey_eligible = FALSE,
               eligibility_reasons_json = '["technical_test_not_methodological"]'::jsonb
         WHERE id = 7
           AND company_id = 9
           AND front_key = 'identity'
           AND diagnosis ILIKE '%fluxo de escrita consultiva%';

        ALTER TABLE public.consultive_assisted_analyses
            ALTER COLUMN analysis_type SET DEFAULT 'technical_test',
            ALTER COLUMN journey_eligible SET DEFAULT FALSE;

        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analyses_company_front_eligible
            ON public.consultive_assisted_analyses(company_id, front_key, journey_eligible);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_consultive_assisted_analyses_company_front_eligible;
        ALTER TABLE public.consultive_assisted_analyses
            DROP CONSTRAINT IF EXISTS ck_consultive_assisted_analyses_analysis_type,
            DROP COLUMN IF EXISTS eligibility_reasons_json,
            DROP COLUMN IF EXISTS journey_eligible,
            DROP COLUMN IF EXISTS analysis_type;
        """
    )
