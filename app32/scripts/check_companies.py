
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
from app import create_app, db
from models.company import Company

app = create_app()

def check():
    with app.app_context():
        # Check ID 36
        c = Company.query.get(36)
        if c:
            print(f"Company 36 found: {c.name}")
        else:
            print("Company 36 NOT found.")
            
        # Check Titan Corp
        c2 = Company.query.filter_by(name="Titan Corp").first()
        if c2:
            print(f"Titan Corp found: {c2.id}")
        else:
            print("Titan Corp NOT found.")

if __name__ == "__main__":
    check()
