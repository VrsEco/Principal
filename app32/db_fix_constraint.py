import os
from sqlalchemy import create_engine, text
try:
    from config import Config
    db_uri = Config.SQLALCHEMY_DATABASE_URI
except:
    db_uri = "postgresql://postgres:postgres@localhost:5432/gestao_versus"

with open("db_fix_output.txt", "w") as f:
    try:
        engine = create_engine(db_uri)
        with engine.connect() as conn:
            f.write("Finding constraints for activity_work_logs...\n")
            res = conn.execute(text("SELECT c.conname, pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_class t ON c.conrelid = t.oid WHERE t.relname = 'activity_work_logs';"))
            for row in res:
                f.write(f"Constraint: {row[0]}, Def: {row[1]}\n")
                
            f.write("Dropping constraint activity_work_logs_activity_type_check\n")
            conn.execute(text("ALTER TABLE activity_work_logs DROP CONSTRAINT IF EXISTS activity_work_logs_activity_type_check;"))
            f.write("Dropped check constraint.\n")
            
            f.write("Adding constraint activity_work_logs_activity_type_check supporting process_instance\n")
            conn.execute(text("ALTER TABLE activity_work_logs ADD CONSTRAINT activity_work_logs_activity_type_check CHECK (activity_type::text = ANY (ARRAY['project'::character varying, 'process'::character varying, 'process_instance'::character varying]::text[]));"))
            f.write("Added new check constraint supporting project, process, process_instance.\n")
            
            conn.commit()
    except Exception as e:
        f.write(f"Error: {e}\n")
