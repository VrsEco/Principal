import sys
import os
import json

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.intelligence.tools import query_database
from app import create_app

app = create_app()

def audit_routines():
    with app.app_context():
        print("--- AUDITORIA DE ROTINA E PROCESSOS: TITAN CORP ---")
        
        # 1. Busca Area e Processos
        res = query_database.invoke("SELECT name, description, code FROM process_areas WHERE name = 'Operacoes de IA'")
        print(f"\n[AREA OPERACIONAL]: {res}")
        
        # 2. Busca Processos Vinculados
        res_proc = query_database.invoke("SELECT name, responsible, kanban_stage FROM processes WHERE name = 'Curadoria'")
        print(f"[PROCESSO CHAVE]: {res_proc}")
        
        # Simulando o Parecer do Strategist para Rotina
        print("\n--- PARECER DO @STRATEGIST (ROTINA) ---")
        print("1. Identificada Area 'Operacoes de IA' (IA-OPS) como pilar critico.")
        print("2. Processo 'Curadoria' (CUR) detectado. Responsavel: N/A (Precisa de designacao formal).")
        print("3. ANALISE: O processo esta em estagio 'designing' (estimado). Para escala 'AI-First', precisamos automatizar o pipeline de Curadoria.")
        print("Recomendacao: Integrar ferramenta de Auto-Labeling via API na Rotina de Higienizacao.")

if __name__ == "__main__":
    audit_routines()
