
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
        print(f"--- NUKING DATA FOR COMPANY {cid} ---")
        
        # 0. Helper with Savepoint
        def run_del(stmt, desc):
            try:
                # Start nested transaction (Savepoint)
                with db.session.begin_nested():
                    res = db.session.execute(text(stmt), {'cid': cid})
                    # print(f"[OK] {desc} ({res.rowcount if res.rowcount != -1 else 'unknown'} rows)")
                    # Keeping output clean
                    pass
                print(f"[OK] {desc}")
            except Exception as e:
                print(f"[ERROR] {desc}: {e}")

        # 1. Projects Ecosystem
        run_del("DELETE FROM project_task_hours_summary WHERE project_task_id IN (SELECT id FROM project_tasks WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid))", "Delete task hours")
        run_del("DELETE FROM project_activity_collaborators WHERE activity_id IN (SELECT id FROM project_activities WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid))", "Delete activity collaborators")
        # run_del("DELETE FROM project_activity_comments WHERE activity_id IN (SELECT id FROM project_activities WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid))", "Delete activity comments") # check table name
        run_del("DELETE FROM project_activities WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid)", "Delete project activities")
        run_del("DELETE FROM project_tasks WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid)", "Delete project tasks")
        
        # 2. OKRs Ecosystem
        run_del("DELETE FROM key_results WHERE okr_global_id IN (SELECT id FROM okrs_global WHERE company_id = :cid)", "Delete Global KRs")
        run_del("DELETE FROM okrs_global WHERE company_id = :cid", "Delete OKRs Global")
        
        run_del("DELETE FROM key_result_areas WHERE okr_area_id IN (SELECT id FROM okrs_area WHERE company_id = :cid)", "Delete Area KRs")
        run_del("DELETE FROM okrs_area WHERE company_id = :cid", "Delete OKRs Area")

        # 3. Plans Ecosystem
        run_del("DELETE FROM plan_implantation_data WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Implantation Data")
        run_del("DELETE FROM plan_section_status WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Section Status")
        run_del("DELETE FROM plan_drivers WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Drivers")
        run_del("DELETE FROM plan_participants WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Participants")
        
        # New tables
        run_del("DELETE FROM plan_products WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Plan Products")
        run_del("DELETE FROM plan_structures WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Plan Structures")
        run_del("DELETE FROM plan_sales_rampup_config WHERE plan_id IN (SELECT id FROM plans WHERE company_id = :cid)", "Delete Sales Rampup")
        
        # 4. Projects (NOW SAFE)
        run_del("DELETE FROM projects WHERE company_id = :cid", "Delete Projects")
        
        # 5. Plans (NOW SAFE?)
        run_del("DELETE FROM plans WHERE company_id = :cid", "Delete Plans")
        
        # 6. Processes Ecosystem
        run_del("DELETE FROM process_steps WHERE routine_id IN (SELECT id FROM routines WHERE company_id = :cid)", "Delete Process Steps")
        run_del("DELETE FROM routine_collaborators WHERE routine_id IN (SELECT id FROM routines WHERE company_id = :cid)", "Delete Routine Collaborators")
        run_del("DELETE FROM routines WHERE company_id = :cid", "Delete Routines")
        
        run_del("DELETE FROM process_instances WHERE company_id = :cid", "Delete Process Instances")
        run_del("DELETE FROM processes WHERE company_id = :cid", "Delete Processes")
        run_del("DELETE FROM macro_processes WHERE company_id = :cid", "Delete Macro Processes")
        run_del("DELETE FROM process_areas WHERE company_id = :cid", "Delete Process Areas")
        
        # 7. Portfolios
        run_del("DELETE FROM portfolios WHERE company_id = :cid", "Delete Portfolios")
        
        # 8. Employees (Only unlinked?)
        # Be careful if user 36 is admin linked to employee.
        # But we reseed.
        run_del("DELETE FROM employees WHERE company_id = :cid", "Delete Employees")

        db.session.commit()
        print("--- NUKE FINAL COMPLETE ---")

if __name__ == "__main__":
    nuke_titan()
