BEGIN;

CREATE TABLE IF NOT EXISTS resource_catalog (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
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
    estimated_useful_life VARCHAR(120),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_resource_catalog_type CHECK (
        type IN ('people', 'inputs', 'facilities', 'digital_it', 'equipment_tools', 'other')
    ),
    CONSTRAINT ck_resource_catalog_capacity_unit CHECK (
        operational_capacity_unit IS NULL
        OR operational_capacity_unit IN ('hour', 'day', 'month')
    ),
    CONSTRAINT ck_resource_catalog_unit_value_non_negative CHECK (unit_value IS NULL OR unit_value >= 0),
    CONSTRAINT ck_resource_catalog_quantity_non_negative CHECK (quantity IS NULL OR quantity >= 0),
    CONSTRAINT ck_resource_catalog_acquisition_non_negative CHECK (acquisition_total_amount IS NULL OR acquisition_total_amount >= 0),
    CONSTRAINT ck_resource_catalog_installation_non_negative CHECK (installation_total_amount IS NULL OR installation_total_amount >= 0),
    CONSTRAINT ck_resource_catalog_monthly_non_negative CHECK (monthly_recurring_amount IS NULL OR monthly_recurring_amount >= 0)
);

CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_type
    ON resource_catalog(company_id, type);

CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_subtype
    ON resource_catalog(company_id, subtype);

CREATE TABLE IF NOT EXISTS process_resource_links (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    process_id INTEGER NOT NULL REFERENCES processes(id),
    process_routine_id INTEGER REFERENCES process_routines(id),
    bpmn_element_id VARCHAR(255),
    resource_id INTEGER NOT NULL REFERENCES resource_catalog(id),
    used_quantity NUMERIC(14, 2),
    usage_percentage NUMERIC(7, 4),
    allocated_monthly_cost NUMERIC(14, 2),
    estimated_cost_per_execution NUMERIC(14, 2),
    capacity_bottleneck_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_process_resource_links_allocated_monthly_non_negative CHECK (
        allocated_monthly_cost IS NULL OR allocated_monthly_cost >= 0
    ),
    CONSTRAINT ck_process_resource_links_execution_cost_non_negative CHECK (
        estimated_cost_per_execution IS NULL OR estimated_cost_per_execution >= 0
    ),
    CONSTRAINT ck_process_resource_links_used_quantity_non_negative CHECK (
        used_quantity IS NULL OR used_quantity >= 0
    ),
    CONSTRAINT ck_process_resource_links_usage_percentage_range CHECK (
        usage_percentage IS NULL OR (usage_percentage >= 0 AND usage_percentage <= 100)
    )
);

CREATE INDEX IF NOT EXISTS ix_process_resource_links_company_process
    ON process_resource_links(company_id, process_id);

CREATE INDEX IF NOT EXISTS ix_process_resource_links_company_resource
    ON process_resource_links(company_id, resource_id);

CREATE INDEX IF NOT EXISTS ix_process_resource_links_routine
    ON process_resource_links(process_routine_id);

CREATE INDEX IF NOT EXISTS ix_process_resource_links_bpmn_element
    ON process_resource_links(bpmn_element_id);

COMMIT;
