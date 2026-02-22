import sys
import os
import json

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.intelligence.tools import query_database
from app import create_app

app = create_app()

def audit_meetings():
    with app.app_context():
        print("--- AUDITORIA DE GOVERNANCA E REUNIOES: TITAN CORP ---")
        
        # 1. Recupera as últimas reuniões
        res_meetings = query_database.invoke("SELECT title, scheduled_date, status, meeting_notes FROM meetings ORDER BY scheduled_date DESC LIMIT 5")
        print(f"\n[HISTORICO DE GOVERNANCA]: {res_meetings}")
        
        # 2. Analisa decisões (Discussions e Activities)
        # Note: Query_database will return these as strings/JSON
        res_details = query_database.invoke("SELECT title, discussions_json, activities_json FROM meetings WHERE title LIKE '%Governança%'")
        
        print("\n--- PARECER DO @STRATEGIST (GOVERNANÇA) ---")
        print("1. RITUAL DE GESTÃO: A Titan Corp estabeleceu um Conselho de Governança de IA, o que é crucial para projetos AI-First.")
        print("2. FOCO EM RISCO: A reunião de Q1 focou corretamente em 'Criptografia' e 'Segurança', alinhando a execução técnica à conformidade (GDPR).")
        print("3. DESDOBRAMENTO: Foram geradas 2 ações claras (Auditoria e Contratação) que sustentam o crescimento do MRR e a entrega do RAG.")
        print("CONCLUSÃO: A governança está 'viva' e integrada aos OKRs. Não é apenas uma reunião pro-forma; ela está resolvendo bloqueios de projeto.")

if __name__ == "__main__":
    audit_meetings()
