
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
except ImportError:
    pass

def nuke_employees(cid=36):
    app = create_app()
    with app.app_context():
        print(f"--- NUKING EMPLOYEES (via Employee ID) FOR COMPANY {cid} ---")
        
        def run_del(stmt, desc):
            try:
                with db.session.begin_nested():
                    res = db.session.execute(text(stmt), {'cid': cid})
                    # print(f"[OK] {desc} ({res.rowcount} rows)")
                    pass
                print(f"[OK] {desc}")
            except Exception as e:
                print(f"[ERROR] {desc}: {e}")

        # 1. References to Employees
        run_del("DELETE FROM activity_work_logs WHERE employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Work Logs (by Emp)")
        run_del("DELETE FROM activity_comments WHERE employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Comments (by Emp)")
        run_del("DELETE FROM project_activity_collaborators WHERE employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Collabs (by Emp)")
        run_del("DELETE FROM project_tasks WHERE employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Tasks (by Emp)")
        run_del("DELETE FROM plan_participants WHERE employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Plan Participants (by Emp)")
        run_del("DELETE FROM team_members WHERE employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Team Members (by Emp)")
        
        # 2. Activities Executor/Responsible?
        # project_activities has executor_id, responsible_id
        run_del("DELETE FROM project_activities WHERE executor_id IN (SELECT id FROM employees WHERE company_id = :cid) OR responsible_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Activities (by Emp)")
        
        # 3. Processes Owner/Responsible
        run_del("DELETE FROM processes WHERE owner_employee_id IN (SELECT id FROM employees WHERE company_id = :cid) OR responsible_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Processes (by Emp)")
        
        # 4. Process Instances
        run_del("DELETE FROM process_instances WHERE executor_id IN (SELECT id FROM employees WHERE company_id = :cid) OR responsible_id IN (SELECT id FROM employees WHERE company_id = :cid) OR owner_employee_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Instances (by Emp)")
        
        # 5. Teams Leader
        run_del("DELETE FROM teams WHERE leader_id IN (SELECT id FROM employees WHERE company_id = :cid)", "Delete Teams (by Leader)")

        # 6. EMPLOYEES
        run_del("DELETE FROM employees WHERE company_id = :cid", "Delete Employees")

        db.session.commit()
        print("--- NUKE EMPLOYEES V2 COMPLETE ---")

if __name__ == "__main__":
    nuke_employees()
