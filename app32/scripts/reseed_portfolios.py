import sys
import os
from datetime import datetime, timedelta

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from models import (
    db, Company, Project, ProjectTask, User, Employee, Portfolio
)

app = create_app()

def deep_seed_portfolios_and_projects():
    with app.app_context():
        print("--- REESTRUTURANDO DEEP DRILL: PORTFOLIOS E PROJETOS ---")
        
        company = Company.query.filter_by(name="Titan Corp").first()
        if not company:
            print("ERRO: Empresa Titan Corp nao encontrada.")
            return

        employee = Employee.query.filter_by(company_id=company.id).first()
        if not employee:
            employee = Employee(company_id=company.id, name="Arthur Dent", email="arthur@titancorp.com")
            db.session.add(employee)
            db.session.commit()

        # 1. PORTFOLIO (O que estava faltando na tela do usuario)
        print("-> Seed Portfolio: Inovacao e IA")
        portfolio = Portfolio.query.filter_by(company_id=company.id, name="Inovacao e IA").first()
        if not portfolio:
            portfolio = Portfolio(
                company_id=company.id,
                code="PORT-IA-2026",
                name="Inovacao e IA",
                responsible_id=employee.id,
                notes="Portfolio focado na transicao para AI-First."
            )
            db.session.add(portfolio)
            db.session.commit()
            print(f"Portfolio criado ID: {portfolio.id}")

        # 2. PROJETO (Vinculando ao Portfolio)
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
                portfolio_id=portfolio.id,
                notes="Projeto vinculado ao Portfolio de IA."
            )
            db.session.add(project)
        else:
            project.portfolio_id = portfolio.id
            print(f"Projeto atualizado com Portfolio ID: {portfolio.id}")

        db.session.commit()
        print(f"\n--- SUCESSO: Portfolios e Projetos integrados. ---")

if __name__ == "__main__":
    deep_seed_portfolios_and_projects()
