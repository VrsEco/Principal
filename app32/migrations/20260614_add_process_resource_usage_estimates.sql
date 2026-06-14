BEGIN;

ALTER TABLE process_resource_links
    ADD COLUMN IF NOT EXISTS used_quantity_per_execution NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS estimated_monthly_instances NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS monthly_used_quantity NUMERIC(14, 2);

UPDATE process_resource_links
SET monthly_used_quantity = COALESCE(monthly_used_quantity, used_quantity)
WHERE monthly_used_quantity IS NULL
  AND used_quantity IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_process_resource_links_used_per_execution_non_negative'
    ) THEN
        ALTER TABLE process_resource_links
            ADD CONSTRAINT ck_process_resource_links_used_per_execution_non_negative
            CHECK (used_quantity_per_execution IS NULL OR used_quantity_per_execution >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_process_resource_links_instances_non_negative'
    ) THEN
        ALTER TABLE process_resource_links
            ADD CONSTRAINT ck_process_resource_links_instances_non_negative
            CHECK (estimated_monthly_instances IS NULL OR estimated_monthly_instances >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_process_resource_links_monthly_used_non_negative'
    ) THEN
        ALTER TABLE process_resource_links
            ADD CONSTRAINT ck_process_resource_links_monthly_used_non_negative
            CHECK (monthly_used_quantity IS NULL OR monthly_used_quantity >= 0);
    END IF;
END $$;

COMMIT;
