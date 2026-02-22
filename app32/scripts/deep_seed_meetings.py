import sys
import os
import json
from datetime import datetime, date

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import db, Company, Project, Meeting

app = create_app()

def deep_seed_meetings():
    with app.app_context():
        print("--- SIMULACAO DE GOVERNANCA E REUNIOES: TITAN CORP ---")
        
        company = Company.query.filter_by(name="Titan Corp").first()
        if not company:
            print("ERRO: Execute o seed da Titan Corp primeiro.")
            return

        project = Project.query.filter_by(company_id=company.id, name="Infraestrutura de RAG Corporativo").first()

        # 1. REUNIAO ESTRATEGICA
        print("-> Seed Reunião: Governança de IA")
        meeting_title = "Conselho de Governança de IA - Q1 2026"
        meeting = Meeting.query.filter_by(company_id=company.id, title=meeting_title).first()
        
        if not meeting:
            # Organizando dados JSON como strings para o modelo
            agenda = [
                {"title": "Revisão do RAG", "time": "15min"},
                {"title": "Análise Financeira (MRR)", "time": "20min"},
                {"title": "Expansão de Time", "time": "15min"}
            ]
            
            discussions = [
                {"topic": "Progresso RAG", "notes": "Arthur Dent confirmou 33% de avanço. O foco agora é a Criptografia."},
                {"topic": "MRR Boost", "notes": "Crescimento de 29% atribuído à pré-venda do RAG para parceiros europeus."}
            ]
            
            activities = [
                {"task": "Auditoria de Segurança", "owner": "Trillian Astra", "deadline": "2026-03-20"},
                {"task": "Contratar 2 Curadores", "owner": "Ford Prefect", "deadline": "2026-03-10"}
            ]

            meeting = Meeting(
                company_id=company.id,
                project_id=project.id if project else None,
                title=meeting_title,
                scheduled_date=date(2026, 2, 19),
                scheduled_time="09:00",
                actual_date=date(2026, 2, 19),
                actual_time="09:15",
                status="completed",
                meeting_notes="Reunião produtiva. Titan Corp está acelerando acima da meta.",
                agenda_json=json.dumps(agenda),
                discussions_json=json.dumps(discussions),
                activities_json=json.dumps(activities),
                participants_json=json.dumps(["Arthur Dent", "Trillian Astra", "Ford Prefect"])
            )
            db.session.add(meeting)
            db.session.commit()
            print(f"Reunião '{meeting_title}' criada com sucesso.")
        else:
            print(f"Reunião '{meeting_title}' já existe.")

        print(f"\n--- SUCESSO: Gestão de Reuniões da Titan Corp alimentada. ---")

if __name__ == "__main__":
    deep_seed_meetings()
