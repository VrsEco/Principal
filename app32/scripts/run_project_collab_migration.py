"""
Executar migration via Flask shell:
docker exec -it app31_app_prod flask shell

Então executar:
>>> from database.postgres_helper import connect as pg_connect
>>> conn = pg_connect()
>>> cursor = conn.cursor()
>>> with open('migrations/20251210_create_project_activity_collaborators.sql', 'r') as f:
...     sql = f.read()
>>> cursor.execute(sql)
>>> conn.commit()
>>> conn.close()
>>> print("Migration executada!")
"""

# Alternativamente, executar SQL diretamente
SQL_MIGRATION = """
BEGIN;

CREATE TABLE IF NOT EXISTS project_activity_collaborators (
    id SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES project_activities(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    role VARCHAR(32) NOT NULL DEFAULT 'executor',
    estimated_hours NUMERIC(10,2) DEFAULT 0,
    worked_hours NUMERIC(10,2) DEFAULT 0,
    notes TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_proj_act_collab_unique
    ON project_activity_collaborators(activity_id, employee_id, role)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_proj_act_collab_employee
    ON project_activity_collaborators(employee_id)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_proj_act_collab_activity
    ON project_activity_collaborators(activity_id)
    WHERE is_deleted = FALSE;

CREATE OR REPLACE FUNCTION trg_proj_act_collab_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_proj_act_collab_updated_at_row'
    ) THEN
        CREATE TRIGGER trg_proj_act_collab_updated_at_row
        BEFORE UPDATE ON project_activity_collaborators
        FOR EACH ROW
        EXECUTE PROCEDURE trg_proj_act_collab_updated_at();
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION trg_update_activity_worked_hours()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE project_activities
    SET worked_hours = (
        SELECT COALESCE(SUM(worked_hours), 0)
        FROM project_activity_collaborators
        WHERE activity_id = COALESCE(NEW.activity_id, OLD.activity_id)
          AND is_deleted = FALSE
    ),
    updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.activity_id, OLD.activity_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_proj_act_collab_update_total'
    ) THEN
        CREATE TRIGGER trg_proj_act_collab_update_total
        AFTER INSERT OR UPDATE OR DELETE ON project_activity_collaborators
        FOR EACH ROW
        EXECUTE PROCEDURE trg_update_activity_worked_hours();
    END IF;
END;
$$;

COMMIT;
"""

if __name__ == '__main__':
    from database.postgres_helper import connect as pg_connect
    conn = pg_connect()
    cursor = conn.cursor()
    try:
        cursor.execute(SQL_MIGRATION)
        conn.commit()
        print("✅ Migration executada com sucesso!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        conn.close()
