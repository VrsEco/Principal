import os
import sys
from datetime import datetime

# Setup paths
sys.path.append(os.getcwd())

from app import create_app
from models import db, User, AgentAction, Employee, ProjectTask, Company
from services.proactive_service import send_morning_summaries

def sync_sequences(db):
    """Sincroniza as sequências do Postgres para evitar erros de ID duplicado"""
    tables = ['projects', 'project_tasks', 'agent_actions', 'companies', 'users', 'employees']
    for table in tables:
        db.session.execute(db.text(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}))"))
    db.session.commit()

def run_test():
    app = create_app()
    with app.app_context():
        sync_sequences(db)
        # 1. Encontra um usuário com Telegram
        user = User.query.filter(User.telegram.isnot(None)).first()
        if not user:
            print("ERRO: Nenhum usuário com Telegram encontrado para o teste.")
            return
        
        print(f"Testando para o usuário: {user.name} (TG: {user.telegram})")

        # 2. Garante que ele tem um vínculo de Employee ativo
        emp = Employee.query.filter_by(user_id=user.id, status='active').first()
        if not emp:
            # Tenta encontrar qualquer vínculo
            emp = Employee.query.filter_by(user_id=user.id).first()
            if emp:
                emp.status = 'active'
                db.session.commit()
            else:
                print("ERRO: Usuário não possui vínculo (Employee) com nenhuma empresa.")
                return

        company = Company.query.get(emp.company_id)
        print(f"Empresa: {company.name}")

        # 3. Cria uma Ação Pendente de IA para teste
        # Limpa anteriores para o teste ficar limpo
        AgentAction.query.filter_by(company_id=company.id, status='pending').delete()
        db.session.commit()
        
        test_action = AgentAction(
            type="business_decision",
            status="pending",
            requesting_agent="business_architect",
            title="Desenho do Processo de Vendas",
            description="Proposta de criação de novo fluxo de funil de vendas para o setor público.",
            payload={"tool": "create_process"},
            company_id=company.id,
            user_id=user.id
        )
        db.session.add(test_action)
        
        # 4. Cria uma tarefa atrasada "fake" se não houver
        # Busca um projeto da empresa
        from models import Project
        project = Project.query.filter_by(company_id=company.id).first()
        if not project:
            # Cria projeto dummy se não houver
            project = Project(
                name="Projeto de Teste",
                company_id=company.id,
                status="in_progress"
            )
            db.session.add(project)
            db.session.flush()

        task = ProjectTask.query.filter_by(project_id=project.id, stage='todo').first()
        if not task:
            task = ProjectTask(
                what="Revisar Metas do Trimestre",
                due_date=datetime(2024, 1, 1).date(), # Bem atrasada
                stage="todo",
                employee_id=emp.id,
                project_id=project.id
            )
            db.session.add(task)
        else:
            # Força atraso para o teste
            task.due_date = datetime(2024, 1, 1).date()
            task.stage = 'todo'

        db.session.commit()
        print("Dados de teste preparados com sucesso.")

        # 5. Dispara o envio
        print("Disparando send_morning_summaries...")
        send_morning_summaries(app)
        print("Processo concluído. Verifique seu Telegram.")

if __name__ == "__main__":
    run_test()
