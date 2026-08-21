BEGIN;

CREATE TABLE IF NOT EXISTS capability_dimensions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    macro_process_id INTEGER REFERENCES macro_processes(id),
    name VARCHAR(160) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE capability_dimensions
    ADD COLUMN IF NOT EXISTS macro_process_id INTEGER REFERENCES macro_processes(id);

DROP INDEX IF EXISTS ix_capability_dimensions_company_order;
ALTER TABLE capability_dimensions DROP CONSTRAINT IF EXISTS uq_capability_dimensions_company_name;

INSERT INTO capability_dimensions (company_id, macro_process_id, name, description, order_index, is_active, created_at, updated_at)
SELECT mp.company_id, mp.id, seed.name, seed.description, seed.order_index, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM macro_processes mp
CROSS JOIN (
    VALUES
        ('Ativos e Estrutura Física', 'Ativos, equipamentos, instalações e condições físicas habilitadoras.', 10),
        ('Pessoas, Papéis e Competências', 'Papéis, equipes e competências necessários à execução.', 20),
        ('Tecnologia, Dados e Sistemas', 'Sistemas, aplicações, integrações e dados necessários à execução.', 30),
        ('Documentos e Conhecimento', 'Documentos, procedimentos, registros e conhecimento controlado.', 40),
        ('Materiais, Insumos e Serviços', 'Materiais, insumos, fornecedores e serviços necessários à execução.', 50)
) AS seed(name, description, order_index)
WHERE NOT EXISTS (
    SELECT 1 FROM capability_dimensions cd
    WHERE cd.company_id = mp.company_id
      AND cd.macro_process_id = mp.id
      AND cd.name = seed.name
);

ALTER TABLE resource_catalog
    ADD COLUMN IF NOT EXISTS macro_process_id INTEGER REFERENCES macro_processes(id),
    ADD COLUMN IF NOT EXISTS dimension_id INTEGER REFERENCES capability_dimensions(id),
    ADD COLUMN IF NOT EXISTS operational_capacity_period VARCHAR(20) DEFAULT 'month',
    ADD COLUMN IF NOT EXISTS max_recommended_utilization_pct NUMERIC(5,2) DEFAULT 100;

UPDATE resource_catalog rc
SET macro_process_id = resolved.macro_process_id
FROM (
    SELECT rc2.id AS resource_id, COALESCE(MIN(p.macro_id), MIN(mp.id)) AS macro_process_id
    FROM resource_catalog rc2
    LEFT JOIN process_resource_links prl ON prl.resource_id = rc2.id AND prl.company_id = rc2.company_id
    LEFT JOIN processes p ON p.id = prl.process_id AND p.company_id = rc2.company_id
    LEFT JOIN macro_processes mp ON mp.company_id = rc2.company_id
    GROUP BY rc2.id
) resolved
WHERE rc.id = resolved.resource_id
  AND rc.macro_process_id IS NULL;

UPDATE resource_catalog rc
SET dimension_id = cd.id
FROM capability_dimensions cd
WHERE cd.company_id = rc.company_id
  AND cd.macro_process_id = rc.macro_process_id
  AND cd.name = CASE
      WHEN rc.type = 'people' THEN 'Pessoas, Papéis e Competências'
      WHEN rc.type = 'digital_it' THEN 'Tecnologia, Dados e Sistemas'
      WHEN rc.type IN ('facilities', 'equipment_tools') THEN 'Ativos e Estrutura Física'
      WHEN rc.type = 'inputs' THEN 'Materiais, Insumos e Serviços'
      ELSE 'Documentos e Conhecimento'
  END;

-- Remove somente os agrupadores globais transitórios, após o remapeamento dos recursos.
DELETE FROM capability_dimensions WHERE macro_process_id IS NULL;

ALTER TABLE capability_dimensions ALTER COLUMN macro_process_id SET NOT NULL;
ALTER TABLE resource_catalog ALTER COLUMN macro_process_id SET NOT NULL;
ALTER TABLE resource_catalog ALTER COLUMN dimension_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_capability_dimensions_macro_name
    ON capability_dimensions(company_id, macro_process_id, name);
CREATE INDEX IF NOT EXISTS ix_capability_dimensions_company_macro_order
    ON capability_dimensions(company_id, macro_process_id, order_index);
CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_macro_dimension
    ON resource_catalog(company_id, macro_process_id, dimension_id);

ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_capacity_unit;
ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_capacity_period;
ALTER TABLE resource_catalog DROP CONSTRAINT IF EXISTS ck_resource_catalog_max_utilization;
ALTER TABLE resource_catalog
    ADD CONSTRAINT ck_resource_catalog_capacity_unit
        CHECK (operational_capacity_unit IS NULL OR operational_capacity_unit IN ('hour', 'unit', 'transaction', 'license', 'person', 'item')),
    ADD CONSTRAINT ck_resource_catalog_capacity_period
        CHECK (operational_capacity_period IS NULL OR operational_capacity_period IN ('day', 'week', 'month', 'quarter', 'year')),
    ADD CONSTRAINT ck_resource_catalog_max_utilization
        CHECK (max_recommended_utilization_pct IS NULL OR (max_recommended_utilization_pct >= 0 AND max_recommended_utilization_pct <= 100));

ALTER TABLE process_resource_links
    ADD COLUMN IF NOT EXISTS required_condition TEXT,
    ADD COLUMN IF NOT EXISTS criticality VARCHAR(20),
    ADD COLUMN IF NOT EXISTS gap_notes TEXT;
ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_usage_percentage_range;
ALTER TABLE process_resource_links DROP CONSTRAINT IF EXISTS ck_process_resource_links_usage_percentage_non_negative;
ALTER TABLE process_resource_links
    ADD CONSTRAINT ck_process_resource_links_usage_percentage_non_negative
        CHECK (usage_percentage IS NULL OR usage_percentage >= 0);

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

COMMIT;
