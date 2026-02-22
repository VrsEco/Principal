from database.postgres_helper import connect


STATEMENTS = [
    "ALTER TABLE processes ADD COLUMN IF NOT EXISTS owner_employee_id INTEGER REFERENCES employees(id)",
    "ALTER TABLE processes ADD COLUMN IF NOT EXISTS responsible_id INTEGER REFERENCES employees(id)",

    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS owner_employee_id INTEGER REFERENCES employees(id)",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS responsible_id INTEGER REFERENCES employees(id)",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS executor_id INTEGER REFERENCES employees(id)",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS notes JSON",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS estimated_hours NUMERIC(10,2) DEFAULT 0",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS worked_hours NUMERIC(10,2) DEFAULT 0",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS actual_hours NUMERIC(10,2)",
    "ALTER TABLE process_instances ADD COLUMN IF NOT EXISTS assigned_collaborators JSON",

    "CREATE INDEX IF NOT EXISTS idx_process_instances_responsible ON process_instances(responsible_id) WHERE responsible_id IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_process_instances_executor ON process_instances(executor_id) WHERE executor_id IS NOT NULL",

    "CREATE SEQUENCE IF NOT EXISTS process_instances_id_seq",
    "SELECT setval('process_instances_id_seq', COALESCE((SELECT MAX(id) FROM process_instances), 0) + 1, false)",
    "ALTER TABLE process_instances ALTER COLUMN id SET DEFAULT nextval('process_instances_id_seq')",
    "ALTER SEQUENCE process_instances_id_seq OWNED BY process_instances.id"
]


def main():
    conn = connect()
    cursor = conn.cursor()
    for statement in STATEMENTS:
        cursor.execute(statement)
        try:
            cursor.fetchone()
        except Exception:
            pass
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
