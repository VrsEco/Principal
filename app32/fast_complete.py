
import os
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from datetime import datetime, date

# Database config
password = quote_plus("*Paraiso1978")
db_url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(db_url)

def complete_task_fast(task_id, completion_date_str):
    comp_date = datetime.strptime(completion_date_str, '%Y-%m-%d').date()
    with engine.connect() as conn:
        # Update project_tasks
        query = text("""
            UPDATE project_tasks 
            SET status = 'completed', 
                stage = 'completed', 
                completion_date = :cdate,
                how = how || :evidence
            WHERE id = :id
        """)
        evidence = f"\n\n✅ EVIDÊNCIA DE CONCLUSÃO ({completion_date_str}): Concluído via Squad de Engenharia (Ajuste Estrutural)"
        conn.execute(query, {"cdate": comp_date, "evidence": evidence, "id": task_id})
        conn.commit()
        print(f"Task {task_id} updated to completed with date {completion_date_str}")

if __name__ == "__main__":
    complete_task_fast(7, "2026-02-22")
