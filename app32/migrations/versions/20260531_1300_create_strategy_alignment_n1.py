"""create strategy alignment n1 domain

Revision ID: 20260531_1300
Revises: 20260531_0900
Create Date: 2026-05-31 13:00:00
"""

from alembic import op


revision = "20260531_1300"
down_revision = "20260531_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_processes_company_id'
            ) THEN
                ALTER TABLE public.processes
                    ADD CONSTRAINT uq_processes_company_id UNIQUE(company_id, id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_indicators_company_id'
            ) THEN
                ALTER TABLE public.indicators
                    ADD CONSTRAINT uq_indicators_company_id UNIQUE(company_id, id);
            END IF;
        END $$;

        CREATE TABLE IF NOT EXISTS public.organizational_identities (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            mission TEXT,
            vision TEXT,
            vision_horizon_year INTEGER,
            purpose TEXT,
            values_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            value_propositions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            differentials_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            pillars_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            strategic_objectives_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            essential_competencies_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            segments_icp_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            policies_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            stakeholders_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            swot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            corporate_indicators_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_organizational_identities_company UNIQUE(company_id),
            CONSTRAINT ck_organizational_identities_vision_year CHECK (
                vision_horizon_year IS NULL OR vision_horizon_year BETWEEN 1900 AND 9999
            )
        );
        CREATE INDEX IF NOT EXISTS ix_organizational_identities_company_id
            ON public.organizational_identities(company_id);

        CREATE TABLE IF NOT EXISTS public.process_strategy_profiles (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_id INTEGER NOT NULL,
            objective TEXT,
            owner VARCHAR(255),
            owner_employee_id INTEGER REFERENCES public.employees(id) ON DELETE SET NULL,
            customer_type VARCHAR(40),
            customer_description TEXT,
            strategic_criticality VARCHAR(20),
            maturity_level VARCHAR(40),
            regulatory_exposure TEXT,
            indicators_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            sipoc_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            cost_resources_volume_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            applicable_policies_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            risks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_process_strategy_profiles_company_process UNIQUE(company_id, process_id),
            CONSTRAINT fk_process_strategy_profiles_company_process
                FOREIGN KEY(company_id, process_id)
                REFERENCES public.processes(company_id, id)
                ON DELETE CASCADE,
            CONSTRAINT ck_process_strategy_profiles_criticality CHECK (
                strategic_criticality IS NULL OR strategic_criticality IN ('alta', 'media', 'baixa')
            ),
            CONSTRAINT ck_process_strategy_profiles_maturity CHECK (
                maturity_level IS NULL OR maturity_level IN (
                    'nao_definido', 'inicial', 'gerenciado', 'padronizado', 'mensurado', 'otimizado'
                )
            )
        );
        CREATE INDEX IF NOT EXISTS ix_process_strategy_profiles_company_process
            ON public.process_strategy_profiles(company_id, process_id);
        CREATE INDEX IF NOT EXISTS ix_process_strategy_profiles_company_id
            ON public.process_strategy_profiles(company_id);
        CREATE INDEX IF NOT EXISTS ix_process_strategy_profiles_process_id
            ON public.process_strategy_profiles(process_id);

        CREATE TABLE IF NOT EXISTS public.process_strategic_alignment_links (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_id INTEGER NOT NULL,
            link_type VARCHAR(60) NOT NULL,
            target_ref_type VARCHAR(60),
            target_ref_id INTEGER,
            target_key VARCHAR(180),
            target_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            contribution_type VARCHAR(80),
            contribution_weight NUMERIC(7, 4),
            notes TEXT,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_process_alignment_links_company_process
                FOREIGN KEY(company_id, process_id)
                REFERENCES public.processes(company_id, id)
                ON DELETE CASCADE,
            CONSTRAINT ck_process_alignment_links_type CHECK (
                link_type IN (
                    'strategic_objective', 'strategic_pillar', 'value_proposition',
                    'differential', 'essential_competence', 'policy'
                )
            ),
            CONSTRAINT ck_process_alignment_links_target_ref_type CHECK (
                target_ref_type IS NULL OR target_ref_type IN (
                    'identity_json', 'okr_global', 'okr_area', 'plan_driver',
                    'indicator', 'policy', 'custom'
                )
            )
        );
        CREATE INDEX IF NOT EXISTS ix_process_alignment_links_company_process
            ON public.process_strategic_alignment_links(company_id, process_id);
        CREATE INDEX IF NOT EXISTS ix_process_alignment_links_company_type
            ON public.process_strategic_alignment_links(company_id, link_type);
        CREATE INDEX IF NOT EXISTS ix_process_alignment_links_target
            ON public.process_strategic_alignment_links(company_id, target_ref_type, target_ref_id, target_key);
        CREATE INDEX IF NOT EXISTS ix_process_alignment_links_company_id
            ON public.process_strategic_alignment_links(company_id);
        CREATE INDEX IF NOT EXISTS ix_process_alignment_links_process_id
            ON public.process_strategic_alignment_links(process_id);

        CREATE TABLE IF NOT EXISTS public.indicator_line_of_sight (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            process_indicator_id INTEGER NOT NULL,
            corporate_indicator_id INTEGER NOT NULL,
            relationship_type VARCHAR(40) NOT NULL DEFAULT 'contributes_to',
            contribution_weight NUMERIC(7, 4),
            notes TEXT,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_indicator_line_of_sight_company_pair
                UNIQUE(company_id, process_indicator_id, corporate_indicator_id),
            CONSTRAINT fk_indicator_los_company_process_indicator
                FOREIGN KEY(company_id, process_indicator_id)
                REFERENCES public.indicators(company_id, id)
                ON DELETE CASCADE,
            CONSTRAINT fk_indicator_los_company_corporate_indicator
                FOREIGN KEY(company_id, corporate_indicator_id)
                REFERENCES public.indicators(company_id, id)
                ON DELETE CASCADE,
            CONSTRAINT ck_indicator_line_of_sight_relationship_type CHECK (
                relationship_type IN ('contributes_to', 'drives', 'rolls_up_to', 'correlates_with')
            )
        );
        CREATE INDEX IF NOT EXISTS ix_indicator_los_company_process_indicator
            ON public.indicator_line_of_sight(company_id, process_indicator_id);
        CREATE INDEX IF NOT EXISTS ix_indicator_los_company_corporate_indicator
            ON public.indicator_line_of_sight(company_id, corporate_indicator_id);
        CREATE INDEX IF NOT EXISTS ix_indicator_los_company_id
            ON public.indicator_line_of_sight(company_id);
        CREATE INDEX IF NOT EXISTS ix_indicator_los_process_indicator_id
            ON public.indicator_line_of_sight(process_indicator_id);
        CREATE INDEX IF NOT EXISTS ix_indicator_los_corporate_indicator_id
            ON public.indicator_line_of_sight(corporate_indicator_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS public.indicator_line_of_sight;
        DROP TABLE IF EXISTS public.process_strategic_alignment_links;
        DROP TABLE IF EXISTS public.process_strategy_profiles;
        DROP TABLE IF EXISTS public.organizational_identities;

        ALTER TABLE public.indicators DROP CONSTRAINT IF EXISTS uq_indicators_company_id;
        ALTER TABLE public.processes DROP CONSTRAINT IF EXISTS uq_processes_company_id;
        """
    )
