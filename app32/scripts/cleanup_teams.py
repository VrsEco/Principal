
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
except ImportError:
    pass

def cleanup_teams(cid=36):
    app = create_app()
    with app.app_context():
        print(f"--- CLEANING TEAMS & EMPLOYEES FOR COMPANY {cid} ---")
        
        def run_del(stmt, desc):
            try:
                with db.session.begin_nested():
                    res = db.session.execute(text(stmt), {'cid': cid})
                print(f"[OK] {desc}")
            except Exception as e:
                print(f"[ERROR] {desc}: {e}")

        # Teams ecosystem
        run_del("DELETE FROM team_members WHERE team_id IN (SELECT id FROM teams WHERE company_id = :cid)", "Delete Team Members")
        run_del("DELETE FROM teams WHERE company_id = :cid", "Delete Teams")
        
        # Employees
        run_del("DELETE FROM employees WHERE company_id = :cid", "Delete Employees")
        
        db.session.commit()
        print("--- CLEANUP COMPLETE ---")

if __name__ == "__main__":
    cleanup_teams()
