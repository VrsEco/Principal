
import os
import sys
sys.path.append(os.getcwd())
from models import db, Project
from app import create_app

def find_project():
    app = create_app()
    with app.app_context():
        # Search by ID 31
        p31 = Project.query.get(31)
        if p31:
            print(f"Project ID 31 found: {p31.name}")
        
        # Search by name containing 31
        others = Project.query.filter(Project.name.contains("31")).all()
        for o in others:
            print(f"Found by name: ID {o.id} | Name: {o.name}")

if __name__ == "__main__":
    find_project()
