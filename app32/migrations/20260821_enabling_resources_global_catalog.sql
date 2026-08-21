BEGIN;

-- Consolida dimensões iguais que foram criadas por macroprocesso.
CREATE TEMP TABLE canonical_capability_dimensions AS
SELECT company_id, name, MIN(id) AS canonical_id
FROM capability_dimensions
GROUP BY company_id, name;

UPDATE resource_catalog rc
SET dimension_id = canonical.canonical_id
FROM capability_dimensions current_dimension
JOIN canonical_capability_dimensions canonical
  ON canonical.company_id = current_dimension.company_id
 AND canonical.name = current_dimension.name
WHERE rc.dimension_id = current_dimension.id
  AND rc.company_id = canonical.company_id
  AND rc.dimension_id <> canonical.canonical_id;

DELETE FROM capability_dimensions dimension
USING canonical_capability_dimensions canonical
WHERE dimension.company_id = canonical.company_id
  AND dimension.name = canonical.name
  AND dimension.id <> canonical.canonical_id;

DROP INDEX IF EXISTS uq_capability_dimensions_macro_name;
DROP INDEX IF EXISTS ix_capability_dimensions_company_macro_order;
DROP INDEX IF EXISTS ix_resource_catalog_company_macro_dimension;
ALTER TABLE capability_dimensions DROP CONSTRAINT IF EXISTS uq_capability_dimensions_macro_name;

ALTER TABLE resource_catalog DROP COLUMN IF EXISTS macro_process_id;
ALTER TABLE capability_dimensions DROP COLUMN IF EXISTS macro_process_id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_capability_dimensions_company_name
    ON capability_dimensions(company_id, name);
CREATE INDEX IF NOT EXISTS ix_capability_dimensions_company_order
    ON capability_dimensions(company_id, order_index);
CREATE INDEX IF NOT EXISTS ix_resource_catalog_company_dimension
    ON resource_catalog(company_id, dimension_id);

DROP TABLE canonical_capability_dimensions;

COMMIT;
