from app import create_app
from models import db, Process

app = create_app()
with app.app_context():
    process = Process.query.get(118)
    if process:
        print(f"ID: {process.id}")
        print(f"Name: {process.name}")
        print(f"Company ID: {process.company_id}")
        print(f"Macro ID: {process.macro_id}")
    else:
        print("Process 118 not found")
