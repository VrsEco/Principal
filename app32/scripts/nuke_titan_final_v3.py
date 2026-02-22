
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
except ImportError:
    pass

def nuke_titan(cid=36):
    app = create_app()
    with app.app_context():
        print(f"--- NUKING DATA V3 FOR COMPANY {cid} ---")
        
        def run_del(stmt, desc):
            try:
                with db.session.begin_nested():
                    res = db.session.execute(text(stmt), {'cid': cid})
                print(f"[OK] {desc}")
            except Exception as e:
                print(f"[ERROR] {desc}: {e}")

        # 1. Activities
        run_del("DELETE FROM activity_comments WHERE company_id = :cid", "Delete Activity Comments")
        run_del("DELETE FROM activity_work_logs WHERE company_id = :cid", "Delete Work Logs")
        
        # 2. Teams (Moved here)
        run_del("DELETE FROM team_members WHERE team_id IN (SELECT id FROM teams WHERE company_id = :cid)", "Delete Team Members")
        run_del("DELETE FROM teams WHERE company_id = :cid", "Delete Teams")

        # 3. Employees (Should work now?)
        run_del("DELETE FROM employees WHERE company_id = :cid", "Delete Employees")

        db.session.commit()
        print("--- NUKE V3 COMPLETE ---")

if __name__ == "__main__":
    nuke_titan()
