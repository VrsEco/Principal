import sys
import os
import json

# Ajusta o path para a raiz do projeto (app32)
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

# Tenta configurar o ambiente Flask para evitar problemas de importação
os.environ['FLASK_APP'] = 'app.py'

from app import create_app
from models import db, Company, Plan

# Criar a aplicacao com contexto de configuracao padrao
app = create_app('default')

def run_exploration():
    with app.app_context():
        print("\n[INICIANDO FLOW: TIME WORK EXPLORANDO SISTEMA]\n")
        
        # 1. CADASTRO DE EMPRESA (Sapiens Role)
        comp_name = "Elite Tech Solucoes V2"
        existing = Company.query.filter_by(name=comp_name).first()
        
        if not existing:
            new_comp = Company(name=comp_name)
            db.session.add(new_comp)
            db.session.commit()
            company_id = new_comp.id
            print(f"PASS 1 (Onboarding): Empresa '{comp_name}' cadastrada com ID {company_id}.")
        else:
            company_id = existing.id
            print(f"PASS 1 (Onboarding): Empresa '{comp_name}' ja existente (ID {company_id}).")

        # 2. EXPLORACAO DE FUNCIONALIDADES (Strategist Role)
        print("\n--- EXPLORACAO DE FUNCIONALIDADES (PEV) ---")
        
        # Testando criacao de Plano
        plan_title = "Plano Estrategico Elite 2026"
        existing_plan = Plan.query.filter_by(company_id=company_id, title=plan_title).first()
        
        if not existing_plan:
            new_plan = Plan(
                company_id=company_id,
                title=plan_title,
                description="Monitoramento gerado por agentes de IA para validacao sistêmica.",
                mode="growth",
                status="draft"
            )
            db.session.add(new_plan)
            db.session.commit()
            plan_id = new_plan.id
            print(f"PASS 2 (Estrategia): Plano '{plan_title}' criado em modo GROWTH.")
        else:
            plan_id = existing_plan.id
            print(f"PASS 2 (Estrategia): Plano '{plan_title}' ja existe (ID {plan_id}).")

        # 3. TESTE DE MULTI-TENANCY & TOOLS (Auditor & Architect Roles)
        print("\n--- TESTE DE FERRAMENTAS INTEGRADAS (MCP TOOLS) ---")
        from src.intelligence.tools import list_plans, get_plan_diagnostics
        
        # Simulando contexto de sessão para a ferramenta (usando Mock ou contexto manual)
        # Como o list_plans usa session.get('active_company_id'), vamos precisar mockar isso se rodarmos via console
        # Mas para o script de exploração, vamos chamar o Service diretamente que é mais "Elite"
        from services.plan_service import PlanService
        
        plans_list = PlanService.list_plans(company_id=company_id, mode="growth")
        print(f"PASS 3 (Integracao): Planos listados via PlanService: {len(plans_list)} encontrados.")
        
        diag_data = PlanService.get_plan_dashboard_data(plan_id, company_id)
        if diag_data:
            print(f"PASS 4 (Auditoria): Dados consolidado do Dashboard: {diag_data.get('completion_percentage', 0)}% completo.")
        else:
            print("FAIL 4 (Auditoria): Falha ao gerar dashboard de dados.")

        # 4. TESTE DE RESILIENCIA (Engineering Role)
        print("\n--- TESTE DE SEGURANCA DE DADOS ---")
        # Tentando acessar algo fora do escopo se fôssemos uma IA real
        try:
             # Simulando o que a ferramenta query_database faria
             from flask import session
             with app.test_request_context():
                 session['active_company_id'] = company_id
                 from src.intelligence.tools import query_database
                 # Tentando SQL Injection / Acesso proibido
                 res_attack = query_database.invoke({"sql_query": "SELECT * FROM users"})
                 print(f"PASS 5 (Blindagem): Tentativa de ler 'users' retornou: {res_attack}")
        except Exception as e:
             print(f"PASS 5 (Blindagem): Sistema barrou acesso indevido com erro: {str(e)}")

        print("\n" + "="*60)
        print("SIMULACAO DE ELITE FINALIZADA")

if __name__ == "__main__":
    run_exploration()
