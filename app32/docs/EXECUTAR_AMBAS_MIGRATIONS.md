# ============================================================================
# SCRIPT COMPLETO: Executar ambas migrations em sequência
# ============================================================================

docker exec -it app31_app_prod flask shell

# Copie e cole TODO o bloco abaixo:

from database.postgres_helper import connect as pg_connect

conn = pg_connect()
cursor = conn.cursor()

# ============================================================================
# MIGRATION 1: Criar tabela project_activities (base)
# ============================================================================
print("📦 Executando migration base...")

base_sql = """
BEGIN;

CREATE TABLE IF NOT EXISTS project_activities (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES company_projects(id) ON DELETE CASCADE,
    code VARCHAR(64),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'planned',
    stage VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'normal',
    deadline DATE,
    estimated_hours NUMERIC(10,2) DEFAULT 0,
    worked_hours NUMERIC(10,2) DEFAULT 0,
    amount NUMERIC(14,2),
    responsible_id INTEGER REFERENCES employees(id),
    executor_id INTEGER REFERENCES employees(id),
    metadata JSON,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_project_activities_project_code
    ON project_activities(project_id, code)
    WHERE code IS NOT NULL AND is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_project_activities_project
    ON project_activities(project_id);

CREATE INDEX IF NOT EXISTS idx_project_activities_responsible
    ON project_activities(responsible_id)
    WHERE responsible_id IS NOT NULL AND is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_project_activities_executor
    ON project_activities(executor_id)
    WHERE executor_id IS NOT NULL AND is_deleted = FALSE;

CREATE OR REPLACE FUNCTION trg_project_activities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_project_activities_updated_at_row'
    ) THEN
        CREATE TRIGGER trg_project_activities_updated_at_row
        BEFORE UPDATE ON project_activities
        FOR EACH ROW
        EXECUTE PROCEDURE trg_project_activities_updated_at();
    END IF;
END;
$$;

COMMIT;
"""

cursor.execute(base_sql)
conn.commit()
print("✅ Tabela project_activities criada!")

# ============================================================================
# MIGRATION 2: Criar tabela project_activity_collaborators
# ============================================================================
print("📦 Executando migration de colaboradores...")

collab_sql = """
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

cursor.execute(collab_sql)
conn.commit()
print("✅ Tabela project_activity_collaborators criada!")

conn.close()
print("\n🎉 Ambas migrations executadas com sucesso!")

exit()
