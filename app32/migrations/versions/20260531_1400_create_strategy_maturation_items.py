"""create strategy maturation backlog

Revision ID: 20260531_1400
Revises: 20260531_1300
Create Date: 2026-05-31 14:00:00
"""

from alembic import op


revision = "20260531_1400"
down_revision = "20260531_1300"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.strategy_maturation_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            block_type VARCHAR(60) NOT NULL,
            item_type VARCHAR(80),
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            source VARCHAR(40) NOT NULL DEFAULT 'ia_inferido',
            confidence NUMERIC(5, 4),
            state VARCHAR(30) NOT NULL DEFAULT 'as_is',
            title VARCHAR(255),
            description TEXT,
            target_ref_type VARCHAR(60),
            target_ref_id INTEGER,
            target_key VARCHAR(180),
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            promoted_ref_type VARCHAR(60),
            promoted_ref_id INTEGER,
            promoted_ref_key VARCHAR(180),
            review_decision VARCHAR(20),
            review_notes TEXT,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            reviewed_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            confirmed_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMP WITHOUT TIME ZONE,
            confirmed_at TIMESTAMP WITHOUT TIME ZONE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_strategy_maturation_items_status CHECK (
                status IN ('draft', 'pending', 'confirmed', 'rejected')
            ),
            CONSTRAINT ck_strategy_maturation_items_source CHECK (
                source IN ('consultor', 'cliente', 'ia_inferido', 'sistema')
            ),
            CONSTRAINT ck_strategy_maturation_items_state CHECK (
                state IN ('as_is', 'to_be', 'target', 'aspirational')
            ),
            CONSTRAINT ck_strategy_maturation_items_block_type CHECK (
                block_type IN ('identity', 'process_profile', 'alignment_link', 'indicator_line_of_sight')
            ),
            CONSTRAINT ck_strategy_maturation_items_confidence CHECK (
                confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
            ),
            CONSTRAINT ck_strategy_maturation_items_review_decision CHECK (
                review_decision IS NULL OR review_decision IN ('confirm', 'reject', 'hold')
            )
        );
        CREATE INDEX IF NOT EXISTS ix_strategy_maturation_items_company_status
            ON public.strategy_maturation_items(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_strategy_maturation_items_company_block
            ON public.strategy_maturation_items(company_id, block_type);
        CREATE INDEX IF NOT EXISTS ix_strategy_maturation_items_company_source
            ON public.strategy_maturation_items(company_id, source);
        CREATE INDEX IF NOT EXISTS ix_strategy_maturation_items_target
            ON public.strategy_maturation_items(company_id, target_ref_type, target_ref_id, target_key);
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.strategy_maturation_items;")
