
import os

from sqlalchemy import create_engine, text

from urllib.parse import quote_plus

# Database config from config.py logic
password = quote_plus("*Paraiso1978")
db_url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"

engine = create_engine(db_url)

def find_activity(search_term):
    with engine.connect() as conn:
        # Search in project_tasks
        query_pt = text("SELECT id, what FROM project_tasks WHERE what ILIKE :search")
        result_pt = conn.execute(query_pt, {"search": f"%{search_term}%"})
        for row in result_pt:
            print(f"TYPE: project_task | ID: {row[0]} | NAME: {row[1]}")
        
        # Search in process_instances
        query_pi = text("SELECT id, title FROM process_instances WHERE title ILIKE :search")
        result_pi = conn.execute(query_pi, {"search": f"%{search_term}%"})
        for row in result_pi:
            print(f"TYPE: process_instance | ID: {row[0]} | NAME: {row[1]}")

if __name__ == "__main__":
    import sys
    search = "asd"
    if len(sys.argv) > 1:
        search = sys.argv[1]
    find_activity(search)
