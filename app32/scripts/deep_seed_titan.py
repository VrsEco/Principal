import sys
import os
import json
from datetime import datetime, timedelta

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import (
    db, Company, Plan, PlanParticipant, PlanSectionStatus, 
    PlanDriver, OKRGlobal, KeyResult, Project, User
)

app = create_app()

def deep_seed():
    with app.app_context():
        print("--- INICIANDO SIMULACAO DE NEGOCIO PROFUNDA: TITAN CORP ---")
        
        # 0. USUARIO
        user = User.query.filter_by(email="admin@titancorp.com").first()
        if not user:
            user = User(name="Admin Titan", email="admin@titancorp.com", role="admin")
            user.set_password("titan123")
            db.session.add(user)
            db.session.commit()

        # 1. EMPRESA E PLANO
        company = Company.query.filter_by(name="Titan Corp").first()
        if not company:
            company = Company(name="Titan Corp")
            db.session.add(company)
            db.session.commit()
        
        plan = Plan.query.filter_by(company_id=company.id, title="Plano de Dominio 2026").first()
        if not plan:
            plan = Plan(
                company_id=company.id,
                title="Plano de Dominio 2026",
                description="Simulacao profunda de planejamento estrategico.",
                mode="growth",
                status="in_progress"
            )
            db.session.add(plan)
            db.session.commit()

        # 2. PARTICIPANTES
        if not PlanParticipant.query.filter_by(plan_id=plan.id, user_id=user.id).first():
            p = PlanParticipant(plan_id=plan.id, user_id=user.id, role="owner")
            db.session.add(p)
        
        # 3. DRIVERS
        drivers = [
            {"type": "driver", "description": "Liderar a transicao global para sistemas AI-First.", "priority": "high"},
            {"type": "opportunity", "description": "Expansao para mercado Europeu.", "priority": "medium"}
        ]
        for d_info in drivers:
            if not PlanDriver.query.filter_by(plan_id=plan.id, description=d_info['description']).first():
                db.session.add(PlanDriver(plan_id=plan.id, **d_info))
        
        # 4. OKRs GLOBAIS
        print("-> Seed: OKRs")
        obj_text = "Expansao Continental"
        obj = OKRGlobal.query.filter_by(plan_id=plan.id, objective=obj_text).first()
        if not obj:
            obj = OKRGlobal(
                company_id=company.id, 
                plan_id=plan.id, 
                objective=obj_text, 
                type="aceleracao", 
                owner=user.name
            )
            db.session.add(obj)
            db.session.commit()
            
            # Key Results
            krs = [
                {"label": "Faturamento Recorrente", "metric": "R$", "target": "50.000.000"},
                {"label": "Market Share", "metric": "%", "target": "15"}
            ]
            for kr_info in krs:
                db.session.add(KeyResult(okr_global_id=obj.id, **kr_info))

        # 5. STATUS DAS SECOES
        sections = [
            "growth_participants", "growth_drivers", "growth_alignment", "growth_okr_global", "growth_projects"
        ]
        for sk in sections:
            sect = PlanSectionStatus.query.filter_by(plan_id=plan.id, section_key=sk).first()
            if not sect:
                sect = PlanSectionStatus(plan_id=plan.id, section_key=sk, status="completed")
                db.session.add(sect)
            else:
                sect.status = "completed"

        db.session.commit()
        print(f"\n--- SUCESSO: O Plano {plan.id} (Titan Corp) esta alimentado. ---")

if __name__ == "__main__":
    deep_seed()
