import os
import datetime
from sqlalchemy import create_engine, text
try:
    from config import Config
    db_uri = Config.SQLALCHEMY_DATABASE_URI
except:
    db_uri = "postgresql://postgres:postgres@localhost:5432/gestao_versus"

engine = create_engine(db_uri)
try:
    with engine.connect() as conn:
        with conn.begin():
            print("Testing occurrences insertion...")
            # Using similar parameters: {'company_id': 5, 'employee_id': None, 'process_id': 19, 'project_id': None, 'title': 'Teste Fabiano Ocorrência', 'description': 'teste', 'type': 'positive', 'score': 5, 'collaborators_ids': '[3, 5]', 'created_at': datetime.datetime(2026, 2, 22, 2, 37, 43, 637827), 'updated_at': datetime.datetime(2026, 2, 22, 2, 37, 43, 637827)}
            params = {
                'company_id': 5, 
                'employee_id': None, 
                'process_id': 19, # Valid process if it exists, otherwise FK might fail, let's use NULL
                'project_id': None, 
                'title': 'Teste Automacao', 
                'description': 'teste', 
                'type': 'positive', 
                'score': 5, 
                'collaborators_ids': '[3, 5]', 
                'created_at': datetime.datetime.now(), 
                'updated_at': datetime.datetime.now()
            }
            conn.execute(text("INSERT INTO occurrences (company_id, employee_id, process_id, project_id, title, description, type, score, collaborators_ids, created_at, updated_at) VALUES (:company_id, :employee_id, :process_id, :project_id, :title, :description, :type, :score, :collaborators_ids, :created_at, :updated_at)"), params)
            print("Successfully inserted occurrence!")
            conn.execute(text("ROLLBACK"))
            print("Rolled back perfectly.")
except Exception as e:
    print(f"Error: {e}")
