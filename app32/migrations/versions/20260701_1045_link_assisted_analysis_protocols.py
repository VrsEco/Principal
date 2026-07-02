"""Link assisted analyses to consultive protocols.

Revision ID: 20260701_1045
Revises: 20260701_1030
Create Date: 2026-07-01
"""

from alembic import op


revision = "20260701_1045"
down_revision = "20260701_1030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.consultive_assisted_analyses
            ADD COLUMN IF NOT EXISTS protocol_id INTEGER NULL,
            ADD COLUMN IF NOT EXISTS protocol_version VARCHAR(40) NULL,
            ADD COLUMN IF NOT EXISTS protocol_source VARCHAR(40) NULL,
            ADD COLUMN IF NOT EXISTS protocol_title VARCHAR(255) NULL,
            ADD COLUMN IF NOT EXISTS protocol_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_consultive_assisted_analyses_protocol_id'
            ) THEN
                ALTER TABLE public.consultive_assisted_analyses
                    ADD CONSTRAINT fk_consultive_assisted_analyses_protocol_id
                    FOREIGN KEY (protocol_id)
                    REFERENCES public.consultive_protocols(id)
                    ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analyses_company_protocol
        ON public.consultive_assisted_analyses (company_id, protocol_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_consultive_assisted_analyses_company_front_protocol_version
        ON public.consultive_assisted_analyses (company_id, front_key, protocol_version);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_consultive_assisted_analyses_company_front_protocol_version;")
    op.execute("DROP INDEX IF EXISTS public.ix_consultive_assisted_analyses_company_protocol;")
    op.execute(
        """
        ALTER TABLE public.consultive_assisted_analyses
            DROP CONSTRAINT IF EXISTS fk_consultive_assisted_analyses_protocol_id,
            DROP COLUMN IF EXISTS protocol_snapshot_json,
            DROP COLUMN IF EXISTS protocol_title,
            DROP COLUMN IF EXISTS protocol_source,
            DROP COLUMN IF EXISTS protocol_version,
            DROP COLUMN IF EXISTS protocol_id;
        """
    )
