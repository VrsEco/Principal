"""Permite múltiplas rotinas de medição por meta.

Revision ID: 20260826_2000
Revises: 20260826_1800
Create Date: 2026-08-26 20:00:00
"""

from alembic import op


revision = "20260826_2000"
down_revision = "20260826_1800"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS indicator_goal_routines (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            goal_id INTEGER NOT NULL REFERENCES indicator_goals(id) ON DELETE CASCADE,
            routine_id INTEGER NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_indicator_goal_routine UNIQUE (company_id, goal_id, routine_id)
        );

        CREATE INDEX IF NOT EXISTS ix_indicator_goal_routines_company_id
            ON indicator_goal_routines(company_id);
        CREATE INDEX IF NOT EXISTS ix_indicator_goal_routines_goal_id
            ON indicator_goal_routines(goal_id);
        CREATE INDEX IF NOT EXISTS ix_indicator_goal_routines_routine_id
            ON indicator_goal_routines(routine_id);

        INSERT INTO indicator_goal_routines (company_id, goal_id, routine_id)
        SELECT g.company_id, g.id, g.routine_id
        FROM indicator_goals g
        JOIN routines r
          ON r.id = g.routine_id
         AND r.company_id = g.company_id
        WHERE g.routine_id IS NOT NULL
        ON CONFLICT (company_id, goal_id, routine_id) DO NOTHING;
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS indicator_goal_routines")
