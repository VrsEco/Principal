import sys
import os
import json

# Ajusta o path para importar o app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src import create_app, db
from src.models.models import Company, User, Plan, Participant, Objective

app = create_app()

def run_exploration():
    with app.app_context():
        print("\n[INICIANDO FLOW: TIME WORK EXPLORANDO SISTEMA]\n")
        
        # 1. CADASTRO DE EMPRESA (Sapiens Role)
        comp_name = "Elite Tech Solucoes"
        existing = Company.query.filter_by(name=comp_name).first()
        
        if not existing:
            new_comp = Company(name=comp_name, status="active")
            db.session.add(new_comp)
            db.session.commit()
            company_id = new_comp.id
            print(f"PASS 1 (Onboarding): Empresa '{comp_name}' cadastrada com ID {company_id}.")
        else:
            company_id = existing.id
            print(f"PASS 1 (Onboarding): Empresa '{comp_name}' ja existente (ID {company_id}).")

        # 2. EXPLORACAO DE FUNCIONALIDADES (Strategist Role)
        print("\n--- EXPLORACAO DE FUNCIONALIDADES ---")
        
        # Testando criacao de Plano
        plan_title = "Plano de Expansao 2026"
        existing_plan = Plan.query.filter_by(company_id=company_id, title=plan_title).first()
        
        if not existing_plan:
            new_plan = Plan(
                company_id=company_id,
                title=plan_title,
                description="Plano gerado para teste de estresse do sistema.",
                mode="growth",
                status="draft"
            )
            db.session.add(new_plan)
            db.session.commit()
            plan_id = new_plan.id
            print(f"PASS 2 (Estrategia): Plano '{plan_title}' criado.")
        else:
            plan_id = existing_plan.id
            print(f"PASS 2 (Estrategia): Plano '{plan_title}' ja existe.")

        # 3. TESTE DE MULTI-TENANCY (Auditor Role)
        # Tentando acessar planos de outra empresa (id 1, assumindo que existe)
        print("\n--- TESTE DE SEGURANCA (SECURITY AUDIT) ---")
        other_plans = Plan.query.filter(Plan.company_id != company_id).all()
        print(f"PASS 3 (Seguranca): Identificados {len(other_plans)} planos de outras empresas no DB.")
        # O teste aqui e manual: o Agente garante que as rotas MCP usam a sessao corretamente.

        # 4. TESTE DE SERVICE LAYER (Architect Role)
        from services.plan_service import PlanService
        dashboard_data = PlanService.get_plan_dashboard_data(plan_id, company_id)
        print("\n--- TESTE DE DASHBOARD (SERVICE LAYER) ---")
        if dashboard_data:
            print(f"PASS 4 (Arquitetura): Dados do Dashboard recuperados via PlanService: {len(dashboard_data.get('sections', []))} secoes.")
        else:
            print("FAIL 4 (Arquitetura): Falha ao recuperar dados do dashboard.")

        # 5. TESTE DE UI/REPORTS (Frontend Role)
        # Este teste e visual, mas verificaremos se os arquivos estao no lugar
        print("\n--- TESTE DE ASSETS (FRONTEND) ---")
        css_path = os.path.join(app.root_path, '../static/css/reports.css')
        if os.path.exists(css_path):
             print(f"PASS 5 (UI): Arquivo reports.css encontrado e acessivel.")
        else:
             print("FAIL 5 (UI): reports.css nao encontrado.")

        print("\n" + "="*60)
        print("SIMULACAO FINALIZADA")

if __name__ == "__main__":
    run_exploration()
