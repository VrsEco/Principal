
import sys
import os

# Add root directory to python path
sys.path.append(os.getcwd())

from app import app
from models import db
from models.process import Process
from models.company import Company
from sqlalchemy import text  

def audit_data():
    with app.app_context():
        print(f"--- DADOS AUDIT V2 ---")
        
        # Check Processes (Model)
        try:
            proc_count = Process.query.count()
            print(f"Total Processes (Model): {proc_count}")
        except Exception as e:
            print(f"Error counting processes: {e}")
            proc_count = 0
            
        # Check Routines (Table Raw SQL)
        try:
            with db.engine.connect() as conn:
                rout_count = conn.execute(text("SELECT count(*) FROM routines")).scalar()
                print(f"Total Routines (Table): {rout_count}")
                
                # Check per Company (First 5 active)
                companies = Company.query.limit(5).all()
                for c in companies:
                    p_c = Process.query.filter_by(company_id=c.id).count()
                    r_c = conn.execute(text("SELECT count(*) FROM routines WHERE company_id = :cid"), {'cid': c.id}).scalar()
                    print(f"Company {c.id} ({c.name}): Processes={p_c}, Routines={r_c}")
        except Exception as e:
            print(f"Error checking routines: {e}")

if __name__ == "__main__":
    audit_data()
