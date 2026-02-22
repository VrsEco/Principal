# -*- coding: ascii -*-
"""
Utility script to ensure the company_projects table exists and legacy plan projects
are migrated into it. Run once if you need to provision the schema manually.
"""

import sqlite3

DB_PATH = "instance/pevapp22.db"

DDL = """
CREATE TABLE IF NOT EXISTS company_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    plan_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planned',
    priority TEXT,
    owner TEXT,
    responsible_id INTEGER,
    start_date DATE,
    end_date DATE,
    okr_area_ref TEXT,
    okr_reference TEXT,
    indicator_reference TEXT,
    activities TEXT,
    notes TEXT,
    code TEXT,
    code_sequence INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
)
"""

TRIGGER = """
CREATE TRIGGER IF NOT EXISTS trg_company_projects_updated_at
AFTER UPDATE ON company_projects
FOR EACH ROW
BEGIN
    UPDATE company_projects
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
"""

MIGRATION = """
INSERT INTO company_projects (
    id, company_id, plan_id, title, description, status, priority,
    owner, responsible_id, start_date, end_date, okr_area_ref,
    okr_reference, indicator_reference, activities, notes,
    code, code_sequence, created_at, updated_at
)
SELECT
    p.id,
    COALESCE(pl.company_id, 0),
    p.plan_id,
    p.title,
    p.description,
    p.status,
    p.priority,
    p.owner,
    NULL,
    p.start_date,
    p.end_date,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    p.created_at,
    p.updated_at
FROM projects p
LEFT JOIN plans pl ON pl.id = p.plan_id
LEFT JOIN company_projects cp ON cp.id = p.id
WHERE cp.id IS NULL;
"""

RESET_SEQUENCE = """
UPDATE sqlite_sequence
SET seq = (SELECT COALESCE(MAX(id), 0) FROM company_projects)
WHERE name = 'company_projects';
"""

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(DDL)
    cursor.execute(TRIGGER)
    cursor.execute(MIGRATION)
    cursor.execute(RESET_SEQUENCE)

    conn.commit()
    conn.close()

    print("? company_projects table ready.")
