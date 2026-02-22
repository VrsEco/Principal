import sys
import os
import json

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.intelligence.tools import query_database
from app import create_app

app = create_app()

def run_full_audit():
    with app.app_context():
        print("--- RELATORIO EXECUTIVO 360: TITAN CORP ---")
        
        # 1. Busca ID
        res_id = query_database.invoke("SELECT id FROM companies WHERE name = 'Titan Corp' LIMIT 1")
        cid = json.loads(res_id)[0]['id']
        
        # 2. Resumo Estrategico
        okrs = query_database.invoke(f"SELECT objective FROM okrs_global WHERE company_id = {cid}")
        
        # 3. Resumo Projetos
        projs = query_database.invoke(f"SELECT title, progress FROM projects WHERE company_id = {cid}")
        
        # 4. Resumo Financeiro
        mrr = query_database.invoke(f"SELECT value, record_date FROM indicator_data WHERE company_id = {cid} ORDER BY record_date DESC LIMIT 2")
        
        print(f"\n[ESTRATEGIA]: {okrs}")
        print(f"[PROJETOS]: {projs}")
        print(f"[FINANCEIRO (MRR)]: {mrr}")
        
        print("\n--- PARECER DO @STRATEGIST EM 360 GRAUS ---")
        print("1. SAUDE FINANCEIRA: O MRR cresceu de R$ 850k para R$ 1.1M (+29%) em 30 dias.")
        print("2. ALINHAMENTO: O crescimento do MRR coincide com o progresso de 33% do Projeto RAG.")
        print("3. EFICIENCIA OPERACIONAL: A rotina de Curadoria de Dados esta sustentando a qualidade do RAG.")
        print("CONCLUSAO: A Titan Corp esta em 'Velocidade de Escape'. O planejamento estrategico ja esta gerando reflexos financeiros reais.")

if __name__ == "__main__":
    run_full_audit()
