"""Cria o catálogo corporativo de recursos habilitadores.

Revision ID: 20260821_1200
Revises: 20260813_1200
Create Date: 2026-08-21 12:00:00
"""

from alembic import op


revision = "20260821_1200"
down_revision = "20260813_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capability_dimensions (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            name VARCHAR(160) NOT NULL,
            description TEXT,
            order_index INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO capability_dimensions (
            company_id, name, description, order_index,
            is_active, created_at, updated_at
        )
        SELECT
            company.id,
            seed.name,
            seed.description,
            seed.order_index,
            TRUE,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM companies company
        CROSS JOIN (
            VALUES
                ('Ativos e Estrutura Física', 'Ativos, equipamentos, instalações e condições físicas habilitadoras.', 10),
                ('Pessoas, Papéis e Competências', 'Papéis, equipes e competências necessários à execução.', 20),
                ('Tecnologia, Dados e Sistemas', 'Sistemas, aplicações, integrações e dados necessários à execução.', 30),
                ('Documentos e Conhecimento', 'Documentos, procedimentos, registros e conhecimento controlado.', 40),
                ('Materiais, Insumos e Serviços', 'Materiais, insumos, fornecedores e serviços necessários à execução.', 50)
        ) AS seed(name, description, order_index)
        WHERE NOT EXISTS (
            SELECT 1
            FROM capability_dimensions existing
            WHERE existing.company_id = company.id
              AND existing.name = seed.name
        );

        CREATE TABLE IF NOT EXISTS resource_catalog (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            dimension_id INTEGER REFERENCES capability_dimensions(id),
            type VARCHAR(40) NOT NULL,
            subtype VARCHAR(120) NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            unit_value NUMERIC(14, 2),
            quantity NUMERIC(14, 2),
            acquisition_total_amount NUMERIC(14, 2),
            installation_total_amount NUMERIC(14, 2),
            monthly_recurring_amount NUMERIC(14, 2),
            operational_capacity_value NUMERIC(14, 2),
            operational_capacity_unit VARCHAR(20),
            operational_capacity_period VARCHAR(20) DEFAULT 'month',
            max_recommended_utilization_pct NUMERIC(5, 2) DEFAULT 100,
            estimated_useful_life VARCHAR(120),
            notes TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        ALTER TABLE resource_catalog
            ADD COLUMN IF NOT EXISTS dimension_id INTEGER REFERENCES capability_dimensions(id),
            ADD COLUMN IF NOT EXISTS operational_capacity_period VARCHAR(20) DEFAULT 'month',
            ADD COLUMN IF NOT EXISTS max_recommended_utilization_pct NUMERIC(5,2) DEFAULT 100;

        UPDATE resource_catalog resource
        SET dimension_id = dimension.id
        FROM capability_dimensions dimension
        WHERE dimension.company_id = resource.company_id
          AND dimension.name = CASE
              WHEN resource.type = 'people' THEN 'Pessoas, Papéis e Competências'
              WHEN resource.type = 'digital_it' THEN 'Tecnologia, Dados e Sistemas'
              WHEN resource.type IN ('facilities', 'equipment_tools') THEN 'Ativos e Estrutura Física'
              WHEN resource.type = 'inputs' THEN 'Materiais, Insumos e Serviços'
              ELSE 'Documentos e Conhecimento'
          END
          AND resource.dimension_id IS NULL;

        CREATE TEMP TABLE canonical_capability_dimensions AS
        SELECT company_id, name, MIN(id) AS canonical_id
        FROM capability_dimensions
        GROUP BY company_id, name;

        UPDATE resource_catalog resource
        SET dimension_id = canonical.canonical_id
        FROM capability_dimensions current_dimension
        JOIN canonical_capability_dimensions canonical
          ON canonical.company_id = current_dimension.company_id
         AND canonical.name = current_dimension.name
        WHERE resource.dimension_id = current_dimension.id
          AND resource.company_id = canonical.company_id
          AND resource.dimension_id <> canonical.canonical_id;

        DELETE FROM capability_dimensions dimension
        USING canonical_capability_dimensions canonical
        WHERE dimension.company_id = canonical.company_id
          AND dimension.name = canonical.name
          AND dimension.id <> canonical.canonical_id;

        DROP TABLE canonical_capability_dimensions;

        DROP INDEX IF EXISTS uq_capability_dimensions_macro_name;
        DROP INDEX IF EXISTS ix_capability_dimensions_company_macro_order;
        DROP INDEX IF EXISTS ix_resource_catalog_company_macro_dimension;
        ALTER TABLE capability_dimensions DROP CONSTRAINT IF EXISTS uq_capability_dimensions_macro_name;
        ALTER TABLE resource_catalog DROP COLUMN IF EXISTS macro_process_id;
        ALTER TABLE capability_dimensions DROP COLUMN IF EXISTS macro_process_id;

        ALTER TABLE resource_catalog ALTER COLUMN dimension_id SET NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_capability_dimensions_company_name
            ON capability_dimensions(company_id, name);
        CREATE INDEX IF NOT EXISTS ix_capability_dimensions_company_order
            ON capability_dimensions(company_id, order_index);
        CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_type
            ON resource_catalog(company_id, type);
        CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_subtype
            ON resource_catalog(company_id, subtype);
        CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_dimension
            ON resource_catalog(company_id, dimension_id);

        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_type;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_capacity_unit;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_capacity_period;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_max_utilization;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_unit_value_non_negative;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_quantity_non_negative;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_acquisition_non_negative;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_installation_non_negative;
        ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_monthly_non_negative;
        ALTER TABLE resource_catalog
            ADD CONSTRAINT ck_resource_catalog_type
                CHECK (type IN ('people', 'inputs', 'facilities', 'digital_it', 'equipment_tools', 'other')),
            ADD CONSTRAINT ck_resource_catalog_capacity_unit
                CHECK (operational_capacity_unit IS NULL OR operational_capacity_unit IN ('hour', 'unit', 'transaction', 'license', 'person', 'item')),
            ADD CONSTRAINT ck_resource_catalog_capacity_period
                CHECK (operational_capacity_period IS NULL OR operational_capacity_period IN ('day', 'week', 'month', 'quarter', 'year')),
            ADD CONSTRAINT ck_resource_catalog_max_utilization
                CHECK (max_recommended_utilization_pct IS NULL OR (max_recommended_utilization_pct >= 0 AND max_recommended_utilization_pct <= 100)),
            ADD CONSTRAINT ck_resource_catalog_unit_value_non_negative
                CHECK (unit_value IS NULL OR unit_value >= 0),
            ADD CONSTRAINT ck_resource_catalog_quantity_non_negative
                CHECK (quantity IS NULL OR quantity >= 0),
            ADD CONSTRAINT ck_resource_catalog_acquisition_non_negative
                CHECK (acquisition_total_amount IS NULL OR acquisition_total_amount >= 0),
            ADD CONSTRAINT ck_resource_catalog_installation_non_negative
                CHECK (installation_total_amount IS NULL OR installation_total_amount >= 0),
            ADD CONSTRAINT ck_resource_catalog_monthly_non_negative
                CHECK (monthly_recurring_amount IS NULL OR monthly_recurring_amount >= 0);

        CREATE TABLE IF NOT EXISTS process_resource_links (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            process_id INTEGER NOT NULL REFERENCES processes(id),
            process_routine_id INTEGER REFERENCES process_routines(id),
            bpmn_element_id VARCHAR(255),
            resource_id INTEGER NOT NULL REFERENCES resource_catalog(id),
            used_quantity NUMERIC(14, 2),
            used_quantity_per_execution NUMERIC(14, 2),
            estimated_monthly_instances NUMERIC(14, 2),
            monthly_used_quantity NUMERIC(14, 2),
            usage_percentage NUMERIC(7, 4),
            allocated_monthly_cost NUMERIC(14, 2),
            estimated_cost_per_execution NUMERIC(14, 2),
            capacity_bottleneck_notes TEXT,
            required_condition TEXT,
            criticality VARCHAR(20),
            gap_notes TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        ALTER TABLE process_resource_links
            ADD COLUMN IF NOT EXISTS used_quantity_per_execution NUMERIC(14, 2),
            ADD COLUMN IF NOT EXISTS estimated_monthly_instances NUMERIC(14, 2),
            ADD COLUMN IF NOT EXISTS monthly_used_quantity NUMERIC(14, 2),
            ADD COLUMN IF NOT EXISTS required_condition TEXT,
            ADD COLUMN IF NOT EXISTS criticality VARCHAR(20),
            ADD COLUMN IF NOT EXISTS gap_notes TEXT;

        UPDATE process_resource_links
        SET monthly_used_quantity = COALESCE(monthly_used_quantity, used_quantity)
        WHERE monthly_used_quantity IS NULL
          AND used_quantity IS NOT NULL;

        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_usage_percentage_range;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_usage_percentage_non_negative;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_criticality;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_allocated_monthly_non_negative;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_execution_cost_non_negative;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_used_quantity_non_negative;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_used_per_execution_non_negative;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_instances_non_negative;
        ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_monthly_used_non_negative;
        ALTER TABLE process_resource_links
            ADD CONSTRAINT ck_process_resource_links_usage_percentage_non_negative
                CHECK (usage_percentage IS NULL OR usage_percentage >= 0),
            ADD CONSTRAINT ck_process_resource_links_criticality
                CHECK (criticality IS NULL OR criticality IN ('low', 'medium', 'high', 'critical')),
            ADD CONSTRAINT ck_process_resource_links_allocated_monthly_non_negative
                CHECK (allocated_monthly_cost IS NULL OR allocated_monthly_cost >= 0),
            ADD CONSTRAINT ck_process_resource_links_execution_cost_non_negative
                CHECK (estimated_cost_per_execution IS NULL OR estimated_cost_per_execution >= 0),
            ADD CONSTRAINT ck_process_resource_links_used_quantity_non_negative
                CHECK (used_quantity IS NULL OR used_quantity >= 0),
            ADD CONSTRAINT ck_process_resource_links_used_per_execution_non_negative
                CHECK (used_quantity_per_execution IS NULL OR used_quantity_per_execution >= 0),
            ADD CONSTRAINT ck_process_resource_links_instances_non_negative
                CHECK (estimated_monthly_instances IS NULL OR estimated_monthly_instances >= 0),
            ADD CONSTRAINT ck_process_resource_links_monthly_used_non_negative
                CHECK (monthly_used_quantity IS NULL OR monthly_used_quantity >= 0);

        CREATE INDEX IF NOT EXISTS ix_process_resource_links_company_process
            ON process_resource_links(company_id, process_id);
        CREATE INDEX IF NOT EXISTS ix_process_resource_links_company_resource
            ON process_resource_links(company_id, resource_id);
        CREATE INDEX IF NOT EXISTS ix_process_resource_links_routine
            ON process_resource_links(process_routine_id);
        CREATE INDEX IF NOT EXISTS ix_process_resource_links_bpmn_element
            ON process_resource_links(bpmn_element_id);

        CREATE TABLE IF NOT EXISTS process_execution_plans (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id),
            process_id INTEGER NOT NULL REFERENCES processes(id),
            frequency_count NUMERIC(14,2) NOT NULL DEFAULT 1 CHECK (frequency_count >= 0),
            frequency_period VARCHAR(20) NOT NULL DEFAULT 'month' CHECK (frequency_period IN ('day', 'week', 'month', 'quarter', 'year')),
            working_days_per_month NUMERIC(6,2) NOT NULL DEFAULT 22 CHECK (working_days_per_month > 0),
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_process_execution_plans_company_process UNIQUE (company_id, process_id)
        );
        CREATE INDEX IF NOT EXISTS ix_process_execution_plans_company_process
            ON process_execution_plans(company_id, process_id);
        """
    )


def downgrade():
    # Estruturas corporativas podem conter dados operacionais; rollback destrutivo
    # deve ser tratado por uma migration corretiva explícita.
    pass
