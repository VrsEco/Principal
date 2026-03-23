from app import create_app
from models import ProjectTask
from schemas.project import project_tasks_schema
from flask import json
import io
import sys

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = create_app()

with app.app_context():
    tasks = ProjectTask.query.filter_by(project_id=1).all()
    out = project_tasks_schema.dump(tasks)
    with open('api_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
