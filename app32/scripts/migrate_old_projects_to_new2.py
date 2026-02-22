import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

def execute_migration():
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM company_projects;")
        old_ids = [r[0] for r in cur.fetchall()]
        
        for oid in old_ids:
            cur.execute(f"SELECT id FROM projects WHERE id = {oid};")
            if cur.fetchone():
                new_id = oid + 90000
                cur.execute(f"UPDATE project_tasks SET project_id = {new_id} WHERE project_id = {oid};")
                cur.execute(f"UPDATE projects SET id = {new_id} WHERE id = {oid};")

        # Migrate PROJECTS with valid company_id
        cur.execute("""
            INSERT INTO projects (
                id, company_id, plan_id, title, notes, status, priority, owner, 
                deadline, created_at, updated_at
            )
            SELECT 
                cp.id, cp.company_id, cp.plan_id, cp.title, 
                COALESCE(cp.description, '') || CHR(10) || COALESCE(cp.notes, ''), 
                cp.status, cp.priority, cp.owner, 
                cp.end_date, 
                CASE WHEN cp.created_at = '' OR cp.created_at IS NULL THEN NOW() ELSE TO_TIMESTAMP(cp.created_at, 'YYYY-MM-DD HH24:MI:SS') END,
                CASE WHEN cp.updated_at = '' OR cp.updated_at IS NULL THEN NOW() ELSE TO_TIMESTAMP(cp.updated_at, 'YYYY-MM-DD HH24:MI:SS') END
            FROM company_projects cp
            INNER JOIN companies c ON c.id = cp.company_id
            ON CONFLICT (id) DO NOTHING;
        """)
        print(f"Migrated {cur.rowcount} company_projects to projects.")

        # Migrate TASKS
        cur.execute("SELECT id FROM project_activities;")
        old_task_ids = [r[0] for r in cur.fetchall()]
        for tid in old_task_ids:
            cur.execute(f"SELECT id FROM project_tasks WHERE id = {tid};")
            if cur.fetchone():
                new_tid = tid + 90000
                cur.execute(f"UPDATE project_tasks SET id = {new_tid} WHERE id = {tid};")

        cur.execute("""
            INSERT INTO project_tasks (
                id, project_id, what, how, status, stage, priority, due_date, 
                estimated_hours, worked_hours, employee_id, created_at, updated_at
            )
            SELECT 
                pa.id, pa.project_id, pa.title, pa.description, pa.status, pa.stage, pa.priority, pa.deadline,
                pa.estimated_hours, pa.worked_hours, pa.executor_id, pa.created_at, pa.updated_at
            FROM project_activities pa
            INNER JOIN projects p ON p.id = pa.project_id
            ON CONFLICT (id) DO NOTHING;
        """)
        print(f"Migrated {cur.rowcount} project_activities to project_tasks.")
        
        cur.execute("SELECT setval('projects_id_seq', (SELECT MAX(id) FROM projects) + 1);")
        cur.execute("SELECT setval('project_tasks_id_seq', (SELECT MAX(id) FROM project_tasks) + 1);")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Failed to migrate: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    execute_migration()
