import sys
import os

# Ensure the app context
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from models import db, Project, Company

app = create_app()

with app.app_context():
    projects = Project.query.all()
    print(f"Total projects in DB: {len(projects)}")
    for p in projects:
        print(f"ID: {p.id}, Title/Name: {p.name}, CompanyID: {p.company_id}, Status: {p.status}")
