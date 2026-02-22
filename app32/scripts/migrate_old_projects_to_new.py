import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get('DATABASE_URL').replace('host.docker.internal', 'localhost')

def execute_migration():
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    try:
        # Move ID=1 if exists in projects to avoid collision (assuming old ones might need ID=1)
        # Check if company_projects has id=1
        cur.execute("SELECT id FROM company_projects WHERE id = 1;")
        collision = cur.fetchone()
        
        cur.execute("SELECT id FROM projects WHERE id = 1;")
        in_new = cur.fetchone()
        
        if collision and in_new:
            print("Resolving ID collision for project ID 1...")
            cur.execute("UPDATE project_tasks SET project_id = 99999 WHERE project_id = 1;")
            cur.execute("UPDATE projects SET id = 99999 WHERE id = 1;")
            print("Project ID 1 moved to 99999.")

        # Let's shift all new projects that share an ID with old projects
        cur.execute("SELECT id FROM company_projects;")
        old_ids = [r[0] for r in cur.fetchall()]
        
        for oid in old_ids:
            cur.execute(f"SELECT id FROM projects WHERE id = {oid};")
            if cur.fetchone():
                new_id = oid + 90000
                cur.execute(f"UPDATE project_tasks SET project_id = {new_id} WHERE project_id = {oid};")
                cur.execute(f"UPDATE projects SET id = {new_id} WHERE id = {oid};")
                print(f"Project ID {oid} moved to {new_id}.")

        # Migrate PROJECTS
        cur.execute("""
            INSERT INTO projects (
                id, company_id, plan_id, title, notes, status, priority, owner, 
                deadline, created_at, updated_at
            )
            SELECT 
                id, company_id, plan_id, title, 
                COALESCE(description, '') || CHR(10) || COALESCE(notes, ''), 
                status, priority, owner, 
                end_date, 
                CASE WHEN created_at = '' THEN NOW() ELSE TO_TIMESTAMP(created_at, 'YYYY-MM-DD HH24:MI:SS') END,
                CASE WHEN updated_at = '' THEN NOW() ELSE TO_TIMESTAMP(updated_at, 'YYYY-MM-DD HH24:MI:SS') END
            FROM company_projects
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
                print(f"Task ID {tid} moved to {new_tid}.")

        cur.execute("""
            INSERT INTO project_tasks (
                id, project_id, what, how, status, stage, priority, due_date, 
                estimated_hours, worked_hours, employee_id, created_at, updated_at
            )
            SELECT 
                id, project_id, title, description, status, stage, priority, deadline,
                estimated_hours, worked_hours, executor_id, created_at, updated_at
            FROM project_activities
            ON CONFLICT (id) DO NOTHING;
        """)
        print(f"Migrated {cur.rowcount} project_activities to project_tasks.")
        
        # Sync sequences
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
