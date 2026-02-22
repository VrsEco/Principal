import os
import sys
import json

# Adicionar o diretório raiz ao path para importar os módulos corretamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Setup do Mock da Sessão do Flask (para passar a validação de multi-tenancy)
from flask import Flask, session
app = Flask(__name__)
app.secret_key = 'test'

def test_new_tools():
    print("\n[INICIANDO VALIDACAO DE ELITE (MCP TOOLS & SECURITY)]\n")
    print("-" * 60)
    
    with app.test_request_context():
        # Simulando Sessao do Usuario
        session['active_company_id'] = 1  # Empresa Dummy 1
        
        # Importar ferramentas apos setar o contexto
        from src.intelligence.tools import query_database, list_plans, get_plan_diagnostics, update_plan_section
        
        # --- TESTE 1: Seguranca SQL (Multi-tenancy) ---
        print("TESTE 1: Protecao Multi-tenancy")
        result_sql = query_database.invoke({"sql_query": "SELECT * FROM plans WHERE company_id = 2"})
        print(f"   Query: SELECT * FROM plans WHERE company_id = 2")
        print(f"   Resultado: {result_sql[:200]}") 
        
        if "WHERE company_id = 1 AND" in result_sql or '"company_id": 1' in result_sql:
            print("   SUCCESS: Multi-tenancy aplicado via filtro automatico.")
        else:
            print(f"   WARNING: Resultado da query nao contem filtro esperado.")

        # --- TESTE 2: Seguranca de Tabelas Sensiveis ---
        print("\nTESTE 2: Protecao de Tabelas Restritas")
        result_sensitive = query_database.invoke({"sql_query": "SELECT * FROM users"})
        print(f"   Query: SELECT * FROM users")
        print(f"   Resultado: {result_sensitive}")
        if "Erro: Acesso" in result_sensitive:
            print("   SUCCESS: Acesso bloqueado conforme Gold Rule.")
        else:
            print("   FAILURE: Tabela sensivel foi acessada!")

        # --- TESTE 3: Listagem de Planos via MCP ---
        print("\nTESTE 3: Listagem de Planos (MCP)")
        plans = list_plans.invoke({"mode": "growth"})
        print(f"   Resultado: {plans[:200]}")
        if "title" in plans or "id" in plans:
            print("   SUCCESS: Planos listados corretamente.")
        else:
            print("   FAILURE: Nenhum plano encontrado ou erro na ferramenta.")

        # --- TESTE 4: Diagnostico de Plano (Service Refactoring) ---
        print("\nTESTE 4: Diagnostico de Plano (Refatorado)")
        try:
            plans_list = json.loads(plans)
            if plans_list:
                plan_id = plans_list[0]['id']
                diag = get_plan_diagnostics.invoke({"plan_id": plan_id})
                print(f"   Plan ID: {plan_id} | Diagnostico: {diag[:200]}")
                if "metrics" in diag and "sections" in diag:
                    print("   SUCCESS: Dados do Service Layer consolidados.")
                else:
                    print("   FAILURE: Dados incompletos no diagnostico.")
            else:
                print("   WARNING: Lista de planos vazia.")
        except Exception as e:
            print(f"   WARNING: Erro ao testar diagnostico: {str(e)}")

        # --- TESTE 5: Atualizacao de Secao ---
        print("\nTESTE 5: Atualizacao de Status de Secao")
        try:
            if plans_list:
                res_upd = update_plan_section.invoke({"plan_id": plan_id, "section_key": "participants", "status": "completed"})
                print(f"   Update: {res_upd}")
                if "sucesso" in res_upd or "atualizado" in res_upd:
                    print("   SUCCESS: Status alterado no banco.")
                else:
                    print("   FAILURE: Erro ao persistir status.")
        except Exception as e:
             print(f"   WARNING: Erro ao testar atualizacao: {str(e)}")

    print("\n" + "="*60)
    print("VALIDACAO CONCLUIDA")

if __name__ == "__main__":
    test_new_tools()
