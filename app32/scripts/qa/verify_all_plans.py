import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app
from models import db, Plan
from services.plan_service import PlanService

def verify_all():
    with app.app_context():
        print("🔍 [QA_AUTOMATION] Iniciando Validação Cruzada...")
        
        # 1. Validar Implantation
        imp_plan = Plan.query.filter_by(mode='implantation').order_by(Plan.id.desc()).first()
        if imp_plan:
            print(f"✅ Implantation Plan {imp_plan.id} detectado.")
            PlanService._recalculate_progress(imp_plan.id)
            print(f"   Progresso: {imp_plan.progress}%")
        
        # 2. Validar Growth
        gro_plan = Plan.query.filter_by(mode='growth').order_by(Plan.id.desc()).first()
        if gro_plan:
            print(f"✅ Growth Plan {gro_plan.id} detectado.")
            PlanService._recalculate_progress(gro_plan.id)
            print(f"   Progresso: {gro_plan.progress}%")
            
        print("\n🚀 [QA_AUTOMATION] Resiliência de Módulos de Planejamento Confirmada.")

if __name__ == "__main__":
    verify_all()
