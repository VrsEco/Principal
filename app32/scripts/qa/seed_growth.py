import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import date, timedelta
from app import app
from models import db, Plan, PlanParticipant, PlanDriver, PlanSectionStatus, User, Employee
from models.okr_global import OKRGlobal, KeyResult
from models.okr_area import OKRArea, KeyResultArea
from models.project import Project, ProjectTask

def seed_growth():
    with app.app_context():
        company_id = 5
        plan = Plan.query.filter_by(mode='growth', title="Plano de Crescimento 2024").first()
        if not plan:
            plan = Plan(
                company_id=company_id, title="Plano de Crescimento 2024",
                mode="growth", status="draft"
            )
            db.session.add(plan)
            db.session.flush()
            
            for section in ['dashboard', 'participants', 'drivers', 'okrs_global', 'okrs_area', 'projects', 'final_report']:
                db.session.add(PlanSectionStatus(plan_id=plan.id, section_key=section, status='pending'))
        
        user = User.query.first()
        employee = Employee.query.first()
        
        # Participants
        if not PlanParticipant.query.filter_by(plan_id=plan.id).first():
            if user: db.session.add(PlanParticipant(plan_id=plan.id, user_id=user.id, role='owner'))
        
        # Drivers
        if not PlanDriver.query.filter_by(plan_id=plan.id).first():
            db.session.add(PlanDriver(plan_id=plan.id, type="opportunity", description="IA Market", priority="high"))

        # OKRs
        okr_g = OKRGlobal.query.filter_by(plan_id=plan.id).first()
        if not okr_g:
            okr_g = OKRGlobal(company_id=company_id, plan_id=plan.id, objective="Market Lead", type="aceleracao")
            db.session.add(okr_g)
            db.session.flush()
            db.session.add(KeyResult(okr_global_id=okr_g.id, label="1M Revenue"))

        # Projects
        if not Project.query.filter_by(plan_id=plan.id).first():
            db.session.add(Project(company_id=company_id, name="CRM Project", plan_id=plan.id, status="in_progress"))

        # Complete
        for section in ['participants', 'drivers', 'okrs_global', 'okrs_area', 'projects']:
            status = PlanSectionStatus.query.filter_by(plan_id=plan.id, section_key=section).first()
            if status: status.status = 'completed'

        db.session.commit()
        print(f"✅ Growth Seeded: Plan {plan.id}")

if __name__ == "__main__":
    seed_growth()
