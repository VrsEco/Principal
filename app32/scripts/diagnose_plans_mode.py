
import sys
import os

sys.path.append(os.getcwd())

from app import app
from models import db
from sqlalchemy import text

def diagnose():
    with app.app_context():
        print("--- DIAGNOSTICO PLANOS ---")
        with db.engine.connect() as conn:
            # Check columns in plans table
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'plans'"))
            columns = [row[0] for row in result]
            print(f"Columns in 'plans': {columns}")
            
            if 'mode' in columns:
                # Check data distribution
                dist = conn.execute(text("SELECT mode, count(*) FROM plans GROUP BY mode")).fetchall()
                print(f"Mode distribution: {dist}")
            else:
                print("COLUMN 'mode' NOT FOUND!")

            if 'plan_mode' in columns:
                 print("COLUMN 'plan_mode' FOUND!")
            else:
                 print("COLUMN 'plan_mode' NOT FOUND (Correct)")

if __name__ == "__main__":
    diagnose()
