
import os
from app import create_app
from models import Process, Company
from flask import session

app = create_app()
with app.app_context():
    count = Process.query.count()
    print(f"Total processes: {count}")
    
    # Check for company 37 (seen in logs)
    count_37 = Process.query.filter_by(company_id=37).count()
    print(f"Processes for company 37: {count_37}")
    
    # List first 5
    processes = Process.query.limit(5).all()
    for p in processes:
        print(f"ID: {p.id}, Name: {p.name}, Company: {p.company_id}")
