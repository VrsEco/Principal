
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app import create_app, db
    from models import Company, Employee, Portfolio, Plan, Project, Process, ProcessRoutine
except ImportError:
    # Fallback if specific imports fail (though they shouldn't)
    from app import create_app, db
    from models.company import Company

app = create_app()

def audit_titan():
    with app.app_context():
        cid = 36
        print(f"--- AUDITORIA TITAN CORP (ID {cid}) ---")
        
        c = Company.query.get(cid)
        if not c:
            print("❌ Company 36 NOT FOUND")
            return
        print(f"✅ Company: {c.name} (Active: {c.is_active})")
        
        # Helper to count
        def count(model, name):
            try:
                n = model.query.filter_by(company_id=cid).count()
                print(f"{'✅' if n > 0 else '⚠️'} {name}: {n}")
            except Exception as e:
                print(f"❌ Error counting {name}: {e}")

        count(Employee, "Employees")
        count(Portfolio, "Portfolios")
        count(Plan, "Plans")
        
        # Raw SQL for detailed check on Projects
        with db.session.connection() as conn:
            projs = conn.execute(text("SELECT count(*) FROM projects WHERE company_id = :cid"), {'cid': cid}).scalar()
            print(f"{'✅' if projs > 0 else '⚠️'} Projects: {projs}")
            
            tasks = conn.execute(text("SELECT count(*) FROM project_tasks WHERE project_id IN (SELECT id FROM projects WHERE company_id = :cid)"), {'cid': cid}).scalar()
            print(f"{'✅' if tasks > 0 else '⚠️'} Project Tasks: {tasks}")
            
            okrs = conn.execute(text("SELECT count(*) FROM okrs_global WHERE company_id = :cid"), {'cid': cid}).scalar()
            print(f"{'✅' if okrs > 0 else '⚠️'} OKRs: {okrs}")
            
            procs = conn.execute(text("SELECT count(*) FROM processes WHERE company_id = :cid"), {'cid': cid}).scalar()
            print(f"{'✅' if procs > 0 else '⚠️'} Processes: {procs}")
            
            routines = conn.execute(text("SELECT count(*) FROM routines WHERE company_id = :cid"), {'cid': cid}).scalar()
            print(f"{'✅' if routines > 0 else '⚠️'} Routines: {routines}")
            
            instances = conn.execute(text("SELECT count(*) FROM process_instances WHERE company_id = :cid"), {'cid': cid}).scalar()
            print(f"ℹ️ Process Instances: {instances}")

if __name__ == "__main__":
    audit_titan()
