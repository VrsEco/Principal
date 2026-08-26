"""Versiona metas recorrentes e permite campanhas sobrepostas.

Revision ID: 20260826_1800
Revises: 20260821_1200
Create Date: 2026-08-26 18:00:00
"""

from alembic import op


revision = "20260826_1800"
down_revision = "20260821_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE indicator_goals
            ADD COLUMN IF NOT EXISTS name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS goal_kind VARCHAR(30) NOT NULL DEFAULT 'base',
            ADD COLUMN IF NOT EXISTS goal_scope VARCHAR(30) NOT NULL DEFAULT 'team',
            ADD COLUMN IF NOT EXISTS composition_mode VARCHAR(30) NOT NULL DEFAULT 'independent';

        UPDATE indicator_goals
        SET goal_scope = CASE WHEN responsible_id IS NULL THEN 'team' ELSE 'individual' END;

        -- Corrige o legado que transformava o início de uma meta recorrente
        -- em sua data final, criando janelas artificiais de um único dia.
        UPDATE indicator_goals
        SET goal_date = NULL,
            period_end = NULL
        WHERE status = 'active'
          AND COALESCE(goal_type, 'monthly') <> 'single'
          AND goal_date = period_start;

        UPDATE indicator_goals
        SET period_end = goal_date
        WHERE period_end IS NULL
          AND goal_date IS NOT NULL
          AND goal_date > period_start;

        ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS ck_indicator_goals_kind;
        ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS ck_indicator_goals_scope;
        ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS ck_indicator_goals_composition;
        ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS ck_indicator_goals_scope_responsible;
        ALTER TABLE indicator_goals DROP CONSTRAINT IF EXISTS ck_indicator_goals_period;
        ALTER TABLE indicator_goals
            ADD CONSTRAINT ck_indicator_goals_kind
                CHECK (goal_kind IN ('base', 'campaign')),
            ADD CONSTRAINT ck_indicator_goals_scope
                CHECK (goal_scope IN ('team', 'individual')),
            ADD CONSTRAINT ck_indicator_goals_composition
                CHECK (composition_mode IN ('independent', 'additive')),
            ADD CONSTRAINT ck_indicator_goals_scope_responsible
                CHECK (
                    (goal_scope = 'team' AND responsible_id IS NULL)
                    OR (goal_scope = 'individual' AND responsible_id IS NOT NULL)
                ),
            ADD CONSTRAINT ck_indicator_goals_period
                CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start);

        CREATE INDEX IF NOT EXISTS ix_indicator_goals_company_indicator_period
            ON indicator_goals(company_id, indicator_id, period_start, period_end);
        CREATE INDEX IF NOT EXISTS ix_indicator_goals_company_responsible_period
            ON indicator_goals(company_id, responsible_id, period_start, period_end);
        """
    )


def downgrade():
    # Metas podem depender da nova semântica; rollback destrutivo exige migration corretiva.
    pass
