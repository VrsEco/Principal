from app import app
from models import db, PlanSectionStatus

def fix_plan_statuses():
    with app.app_context():
        # 1. Fix 'complete' typo
        typos = PlanSectionStatus.query.filter_by(status='complete').all()
        for t in typos:
            print(f"Fixing typo for Plan {t.plan_id}, Section {t.section_key}: complete -> completed")
            t.status = 'completed'
        
        # 2. Ensure 'projects' section exists for Plan 10
        plan_id = 10
        p_status = PlanSectionStatus.query.filter_by(plan_id=plan_id, section_key='projects').first()
        if not p_status:
            print(f"Creating missing 'projects' status for Plan {plan_id}")
            p_status = PlanSectionStatus(plan_id=plan_id, section_key='projects', status='pending')
            db.session.add(p_status)
        else:
            print(f"'projects' status for Plan {plan_id} already exists: {p_status.status}")

        db.session.commit()
        print("Database fixes applied.")

if __name__ == "__main__":
    fix_plan_statuses()
