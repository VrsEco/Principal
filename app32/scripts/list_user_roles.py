import sys
import os
sys.path.append(os.getcwd())
from app import app
from models.user import User

with app.app_context():
    users = User.query.all()
    print("--- USERS LIST ---")
    for u in users:
        print(f"ID: {u.id} | Email: {u.email} | Name: {u.name} | Role: {u.role}")
