
import os
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Database config
password = quote_plus("*Paraiso1978")
db_url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(db_url)

def get_task_details(task_id):
    with engine.connect() as conn:
        query = text("SELECT id, what, status, stage, completion_date FROM project_tasks WHERE id = :id")
        result = conn.execute(query, {"id": task_id}).fetchone()
        if result:
            print(f"ID: {result[0]} | WHAT: {result[1]} | STATUS: {result[2]} | STAGE: {result[3]} | COMP_DATE: {result[4]}")
        else:
            print("Task not found")

if __name__ == "__main__":
    import sys
    tid = 7
    if len(sys.argv) > 1:
        tid = int(sys.argv[1])
    get_task_details(tid)
