
import os
import sys
sys.path.append(os.getcwd())
from models import db, Project
from app import create_app

def list_projects():
    app = create_app()
    with app.app_context():
        projects = Project.query.limit(20).all()
        print("\n--- Lista de Projetos (Top 20) ---")
        for p in projects:
            print(f"ID: {p.id} | Name: {p.name}")
        print("----------------------------------\n")

if __name__ == "__main__":
    list_projects()
