import sys
import os
from datetime import datetime, timedelta

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import (
    db, Company, Project, ProjectTask, User, Employee
)

app = create_app()

def deep_seed_projects():
    with app.app_context():
        print("--- SIMULACAO DE GESTAO DE PROJETOS ESTRATEGICOS: TITAN CORP ---")
        
        company = Company.query.filter_by(name="Titan Corp").first()
        if not company:
            print("ERRO: Execute o seed da Titan Corp primeiro.")
            return

        # Busca ou cria colaborador
        employee = Employee.query.filter_by(company_id=company.id).first()
        if not employee:
            employee = Employee(company_id=company.id, name="Arthur Dent", email="arthur@titancorp.com")
            db.session.add(employee)
            db.session.commit()

        # 1. PROJETO
        print("-> Seed Projeto: Infraestrutura de RAG Corporativo")
        project = Project.query.filter_by(company_id=company.id, name="Infraestrutura de RAG Corporativo").first()
        if not project:
            project = Project(
                company_id=company.id,
                name="Infraestrutura de RAG Corporativo",
                owner="Arthur Dent",
                status="in_progress",
                deadline=(datetime.now() + timedelta(days=90)).date(),
                budget="R$ 150.000,00",
                priority="high",
                notes="Projeto critico para a meta de faturamento de R$ 50M."
            )
            db.session.add(project)
            db.session.commit()

        # 2. TAREFAS (ProjectTask)
        print("-> Seed Tarefas (Estrategia 5W2H)")
        tasks = [
            {
                "what": "Arquitetura do Banco de Vetores",
                "who": "Arthur Dent",
                "how": "Avaliar latencia e custo entre ChromaDB e Pinecone.",
                "due_date": (datetime.now() + timedelta(days=15)).date(),
                "status": "completed",
                "stage": "completed",
                "priority": "high"
            },
            {
                "what": "Criptografia de Dados em Repouso",
                "who": "Trillian Astra",
                "how": "Implementar AES-256 no storage de vetores conforme GPDR.",
                "due_date": (datetime.now() + timedelta(days=30)).date(),
                "status": "in_progress",
                "stage": "executing",
                "priority": "urgent"
            },
            {
                "what": "Integracao com ERP - Pipeline de Dados",
                "who": "Ford Prefect",
                "how": "Criar webhooks para atualizar vetores quando houver novos contratos.",
                "due_date": (datetime.now() + timedelta(days=45)).date(),
                "status": "planned",
                "stage": "inbox",
                "priority": "normal"
            }
        ]
        
        for t_info in tasks:
            if not ProjectTask.query.filter_by(project_id=project.id, what=t_info['what']).first():
                task = ProjectTask(
                    project_id=project.id,
                    employee_id=employee.id,
                    **t_info
                )
                db.session.add(task)
        
        # 3. ATUALIZAR PROGRESSO DO PROJETO
        db.session.commit()
        project.update_progress()
        db.session.commit()
        
        print(f"\n--- SUCESSO: Gestao de Projetos da Titan Corp alimentada. Progresso: {project.progress}% ---")

if __name__ == "__main__":
    deep_seed_projects()
