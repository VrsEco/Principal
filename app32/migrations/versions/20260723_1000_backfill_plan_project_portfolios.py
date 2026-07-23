"""backfill plan project portfolios

Revision ID: 20260723_1000
Revises: 20260721_2130
Create Date: 2026-07-23 10:00:00
"""

from alembic import op


revision = "20260723_1000"
down_revision = "20260721_2130"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        INSERT INTO portfolios (
            company_id,
            code,
            name,
            notes,
            created_at,
            updated_at
        )
        SELECT DISTINCT
            plan.company_id,
            'PLAN-' || plan.id::text,
            plan.title,
            '[APP32_PLAN_PORTFOLIO] Portfólio criado pelo backfill do Planejamento Estratégico #' || plan.id::text || '.',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM plans AS plan
        JOIN projects AS project
          ON project.plan_id = plan.id
         AND project.company_id = plan.company_id
        WHERE project.portfolio_id IS NULL
          AND COALESCE(project.is_deleted, FALSE) = FALSE
          AND NOT EXISTS (
              SELECT 1
              FROM portfolios AS existing
              WHERE existing.company_id = plan.company_id
                AND existing.code = 'PLAN-' || plan.id::text
          )
        """
    )
    op.execute(
        """
        UPDATE projects AS project
        SET portfolio_id = portfolio.id,
            updated_at = CURRENT_TIMESTAMP
        FROM plans AS plan
        JOIN portfolios AS portfolio
          ON portfolio.company_id = plan.company_id
         AND portfolio.code = 'PLAN-' || plan.id::text
        WHERE project.plan_id = plan.id
          AND project.company_id = plan.company_id
          AND project.portfolio_id IS NULL
          AND COALESCE(project.is_deleted, FALSE) = FALSE
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE projects AS project
        SET portfolio_id = NULL,
            updated_at = CURRENT_TIMESTAMP
        FROM portfolios AS portfolio
        WHERE project.portfolio_id = portfolio.id
          AND portfolio.notes LIKE '[APP32_PLAN_PORTFOLIO]%'
        """
    )
    op.execute(
        """
        DELETE FROM portfolios AS portfolio
        WHERE portfolio.notes LIKE '[APP32_PLAN_PORTFOLIO]%'
          AND NOT EXISTS (
              SELECT 1
              FROM projects AS project
              WHERE project.portfolio_id = portfolio.id
          )
        """
    )
