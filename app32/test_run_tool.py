
import os
import sys
from flask import Flask

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app
from models import db
from src.intelligence.tools import complete_task

def run_test():
    app = create_app()
    with app.app_context():
        # Concluir a atividade 7 com data de ontem (2026-02-22)
        print("Executando complete_task para ID 7 com data 2026-02-22...")
        result = complete_task.invoke({
            "task_type": "project_task",
            "task_id": 7,
            "evidence_description": "Concluído via Squad de Engenharia (Teste de Correção)",
            "completion_date": "2026-02-22"
        })
        print(f"RESULTADO: {result}")

if __name__ == "__main__":
    run_test()
