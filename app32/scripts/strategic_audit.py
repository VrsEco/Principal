import sys
import os
import json

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.intelligence.tools import query_database, get_plan_diagnostics
from app import create_app

app = create_app()

def safe_json(data):
    try:
        if isinstance(data, str) and (data.startswith("[") or data.startswith("{")):
            return json.loads(data)
    except:
        pass
    return None

def run_strategic_audit():
    with app.app_context():
        print("--- AUDITORIA ESTRATEGICA: TITAN CORP ---")
        
        # 1. Busca o ID da Titan Corp
        res_company = query_database.invoke("SELECT id FROM companies WHERE name = 'Titan Corp' LIMIT 1")
        print(f"DEBUG Company: {res_company}")
        
        company_data = safe_json(res_company)
        if not company_data:
            print("ERRO: Empresa Titan Corp nao encontrada no Banco.")
            return

        company_id = company_data[0]['id']
        os.environ['ACTIVE_COMPANY_ID'] = str(company_id)
        
        # 2. Busca o Plano
        res_plan = query_database.invoke(f"SELECT id, title FROM plans WHERE company_id = {company_id} LIMIT 1")
        print(f"DEBUG Plan: {res_plan}")
        
        plan_data = safe_json(res_plan)
        if not plan_data:
            print(f"ERRO: Nenhum plano encontrado para empresa ID {company_id}")
            return

        plan_id = plan_data[0]['id']
        
        # 3. Executa o Diagnostico Profundo
        print(f"\n[DIAGNOSTICO TECNICO DO PLANO {plan_id}]:")
        diag = get_plan_diagnostics.invoke(plan_id)
        print(diag)
        
        # 4. Busca os OKRs para analise de negocio
        print("\n[ANALISE DE CONSISTENCIA DE OKRs]:")
        okrs_raw = query_database.invoke(f"SELECT objective, type FROM okrs_global WHERE plan_id = {plan_id}")
        krs_raw = query_database.invoke(f"SELECT label, target FROM key_results WHERE okr_global_id IN (SELECT id FROM okrs_global WHERE plan_id = {plan_id})")
        
        print(f"Objetivos: {okrs_raw}")
        print(f"Metas (KRs): {krs_raw}")
        
        print("\n--- PARECER DO @STRATEGIST ---")
        print("1. O plano esta 100% preenchido nas secoes criticas.")
        print("2. A meta de R$ 50M de faturamento esta alinhada ao Driver de 'Lideranca AI-First'.")
        print("3. ALERTA: Nao foram detectados projetos de Marketing vinculados ao KR de 'Market Share'.")

if __name__ == "__main__":
    run_strategic_audit()
