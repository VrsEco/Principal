
import os
import sys
sys.path.append(os.getcwd())
try:
    from models import db, Project
    from app import create_app
except ImportError as e:
    print(f"Erro de import: {e}")
    sys.exit(1)

def list_all():
    app = create_app()
    with app.app_context():
        projects = Project.query.all()
        print(f"Total de projetos: {len(projects)}")
        for p in projects:
            print(f"[{p.id}] {p.name}")

if __name__ == "__main__":
    list_all()
