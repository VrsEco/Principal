"""create tenant-safe N:N links between indicators and monitored entities

Revision ID: 20260614_1200
Revises: 20260606_1600
Create Date: 2026-06-14 12:00:00.000000
"""

from alembic import op


revision = "20260614_1200"
down_revision = "20260606_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.indicator_entity_links (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id),
            indicator_id INTEGER NOT NULL,
            target_type VARCHAR(40) NOT NULL,
            target_id INTEGER NULL,
            target_ref VARCHAR(180) NOT NULL,
            target_label VARCHAR(255) NULL,
            role VARCHAR(30) NOT NULL DEFAULT 'primary',
            health_dimension VARCHAR(40) NULL,
            weight NUMERIC(7, 4) NULL,
            relationship_type VARCHAR(60) NULL,
            notes TEXT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'fk_indicator_entity_links_company_indicator'
            ) THEN
                ALTER TABLE public.indicator_entity_links
                    ADD CONSTRAINT fk_indicator_entity_links_company_indicator
                    FOREIGN KEY (company_id, indicator_id)
                    REFERENCES public.indicators(company_id, id)
                    ON DELETE CASCADE;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'uq_indicator_entity_links_company_indicator_target'
            ) THEN
                ALTER TABLE public.indicator_entity_links
                    ADD CONSTRAINT uq_indicator_entity_links_company_indicator_target
                    UNIQUE (company_id, indicator_id, target_type, target_ref);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_indicator_entity_links_target_type'
            ) THEN
                ALTER TABLE public.indicator_entity_links
                    ADD CONSTRAINT ck_indicator_entity_links_target_type
                    CHECK (target_type IN ('process', 'project', 'okr_global', 'okr_area', 'strategic_objective'));
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_indicator_entity_links_role'
            ) THEN
                ALTER TABLE public.indicator_entity_links
                    ADD CONSTRAINT ck_indicator_entity_links_role
                    CHECK (role IN ('primary', 'secondary', 'diagnostic', 'control'));
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_indicator_entity_links_health_dimension'
            ) THEN
                ALTER TABLE public.indicator_entity_links
                    ADD CONSTRAINT ck_indicator_entity_links_health_dimension
                    CHECK (
                        health_dimension IS NULL OR
                        health_dimension IN ('prazo', 'qualidade', 'custo', 'risco', 'capacidade', 'conformidade', 'resultado', 'estrategia')
                    );
            END IF;
        END
        $$;

        CREATE INDEX IF NOT EXISTS ix_indicator_entity_links_company_target
            ON public.indicator_entity_links(company_id, target_type, target_ref);
        CREATE INDEX IF NOT EXISTS ix_indicator_entity_links_company_indicator
            ON public.indicator_entity_links(company_id, indicator_id);

        INSERT INTO public.indicator_entity_links (
            company_id, indicator_id, target_type, target_id, target_ref,
            target_label, role, health_dimension, relationship_type, notes,
            is_active, created_at, updated_at
        )
        SELECT i.company_id, i.id, 'process', i.process_id, i.process_id::TEXT,
               p.name, 'primary', NULL, 'legacy_process_id',
               'Backfill automático a partir de indicators.process_id.',
               COALESCE(i.is_active, TRUE), NOW(), NOW()
          FROM public.indicators i
          JOIN public.processes p
            ON p.company_id = i.company_id
           AND p.id = i.process_id
         WHERE i.process_id IS NOT NULL
        ON CONFLICT (company_id, indicator_id, target_type, target_ref) DO NOTHING;

        INSERT INTO public.indicator_entity_links (
            company_id, indicator_id, target_type, target_id, target_ref,
            target_label, role, health_dimension, relationship_type, notes,
            is_active, created_at, updated_at
        )
        SELECT i.company_id, i.id, 'project', i.project_id, i.project_id::TEXT,
               p.title, 'primary', NULL, 'legacy_project_id',
               'Backfill automático a partir de indicators.project_id.',
               COALESCE(i.is_active, TRUE), NOW(), NOW()
          FROM public.indicators i
          JOIN public.projects p
            ON p.company_id = i.company_id
           AND p.id = i.project_id
         WHERE i.project_id IS NOT NULL
        ON CONFLICT (company_id, indicator_id, target_type, target_ref) DO NOTHING;

        INSERT INTO public.indicator_entity_links (
            company_id, indicator_id, target_type, target_id, target_ref,
            target_label, role, health_dimension, relationship_type, notes,
            is_active, created_at, updated_at
        )
        SELECT i.company_id, i.id, 'process', i.source_id, i.source_id::TEXT,
               p.name, 'primary', NULL, 'legacy_source_module',
               'Backfill automático a partir de indicators.source_module/source_id.',
               COALESCE(i.is_active, TRUE), NOW(), NOW()
          FROM public.indicators i
          JOIN public.processes p
            ON p.company_id = i.company_id
           AND p.id = i.source_id
         WHERE i.source_id IS NOT NULL
           AND LOWER(COALESCE(i.source_module, '')) IN ('processo', 'process')
        ON CONFLICT (company_id, indicator_id, target_type, target_ref) DO NOTHING;

        INSERT INTO public.indicator_entity_links (
            company_id, indicator_id, target_type, target_id, target_ref,
            target_label, role, health_dimension, relationship_type, notes,
            is_active, created_at, updated_at
        )
        SELECT i.company_id, i.id, 'project', i.source_id, i.source_id::TEXT,
               p.title, 'primary', NULL, 'legacy_source_module',
               'Backfill automático a partir de indicators.source_module/source_id.',
               COALESCE(i.is_active, TRUE), NOW(), NOW()
          FROM public.indicators i
          JOIN public.projects p
            ON p.company_id = i.company_id
           AND p.id = i.source_id
         WHERE i.source_id IS NOT NULL
           AND LOWER(COALESCE(i.source_module, '')) IN ('projeto', 'project')
        ON CONFLICT (company_id, indicator_id, target_type, target_ref) DO NOTHING;
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS public.indicator_entity_links;")
