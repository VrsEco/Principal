import sys
import os
import json

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.intelligence.tools import query_database
from app import create_app

app = create_app()

def audit_projects():
    with app.app_context():
        print("--- AUDITORIA DE PROJETOS E EXECUCAO: TITAN CORP ---")
        
        # 1. Recupera Projetos
        res_projs = query_database.invoke("SELECT title, status, progress, priority FROM projects WHERE title LIKE '%RAG%'")
        print(f"\n[PROJETOS ESTRATEGICOS]: {res_projs}")
        
        # 2. Recupera Tarefas Criticas
        res_tasks = query_database.invoke("SELECT what, stage, priority FROM project_tasks WHERE priority = 'urgent' OR priority = 'high'")
        print(f"[TAREFAS CRITICAS BOLSA DE VALORES]: {res_tasks}")
        
        # Simulando o Parecer do Strategist para Projetos
        print("\n--- PARECER DO @STRATEGIST (PROJETOS) ---")
        print("1. PROJETO RAG: Progresso de 33% esta saudavel para a fase inicial.")
        print("2. RISCO: A tarefa 'Criptografia de Dados' esta marcada como URGENTE. Sem ela, o projeto nao pode avancar para integracao com ERP.")
        print("3. ANALISE: Existe uma boa distribuicao de responsabilidades entre CEO (Arthur) e CFO (Trillian).")
        print("Recomendacao: Alocar recursos adicionais para a tarefa de Criptografia para reduzir o risco de atraso na homologacao de seguranca.")

if __name__ == "__main__":
    audit_projects()
