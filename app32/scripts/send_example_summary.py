import os
import sys
import json
from datetime import datetime, date, timedelta

# Setup paths
sys.path.append(os.getcwd())

from app import create_app
from models import db, User, Employee, Company, Project, ProjectTask, AgentAction
from models.process import ProcessInstance, Process
from models.meeting import Meeting
from services.proactive_service import get_user_summary_report
from api.webhooks.telegram_webhook import bot

def sync_sequences(db):
    """Sincroniza as sequências do Postgres"""
    tables = ['projects', 'project_tasks', 'companies', 'users', 'employees', 'meetings', 'process_instances', 'agent_actions']
    for table in tables:
        try:
            db.session.execute(db.text(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}))"))
        except:
            pass
    db.session.commit()

def run_test():
    app = create_app()
    with app.app_context():
        sync_sequences(db)
        
        # 1. Encontrar usuário Fabiano
        user = User.query.filter(User.telegram == '8507771166').first()
        if not user:
            user = User.query.filter(User.telegram.isnot(None)).first()
            if not user:
                print("ERRO: Nenhum usuário com Telegram encontrado.")
                return
        
        print(f"Gerando exemplo para: {user.name} (TG: {user.telegram})")

        # 2. Get Employee and Company
        emp = Employee.query.filter_by(user_id=user.id, status='active').first()
        if not emp:
            print("ERRO: Usuário sem vínculo ativo.")
            return

        cid = emp.company_id
        today = date.today()
        start_week = today - timedelta(days=(today.weekday() + 1) % 7)
        
        # Limpar dados de teste anteriores
        Meeting.query.filter(Meeting.title.ilike('%[EXEMPLO]%')).delete()
        ProjectTask.query.filter(ProjectTask.what.ilike('%[EXEMPLO]%')).delete()
        ProcessInstance.query.filter(ProcessInstance.title.ilike('%[EXEMPLO]%')).delete()
        AgentAction.query.filter(AgentAction.title.ilike('%[EXEMPLO]%')).delete()
        db.session.commit()

        # 3. Criar Itens
        
        # Ação pendente
        db.session.add(AgentAction(
            type="business_decision", status="pending", requesting_agent="business_architect",
            title="[EXEMPLO] Aprovação de Novo Layout Industrial", 
            description="Necessário validar o fluxo logístico antes da implementação.",
            company_id=cid, user_id=user.id
        ))

        # Processo & Projeto para vincular
        proc = Process.query.filter_by(company_id=cid).first()
        if not proc:
            proc = Process(name="Processo Operacional", company_id=cid, code="OP-001")
            db.session.add(proc)
            db.session.flush()

        project = Project.query.filter_by(company_id=cid).first()
        if not project:
            project = Project(name="Gestão Operacional", company_id=cid, status='active')
            db.session.add(project)
            db.session.flush()

        # Atrasados (3 Processos, 1 Projeto)
        past_date = today - timedelta(days=5)
        for i in range(1, 4):
            db.session.add(ProcessInstance(
                company_id=cid, process_id=proc.id, title=f"[EXEMPLO] Conferência de Estoque {i}",
                due_date=past_date, status='open', responsible_id=emp.id
            ))
        
        db.session.add(ProjectTask(
            what="[EXEMPLO] Relatório de Desempenho Mensal", due_date=past_date,
            stage="todo", employee_id=emp.id, project_id=project.id
        ))

        # Esta Semana (2 Processos, 3 Projetos, 2 Reuniões)
        week_date = start_week + timedelta(days=3)
        if week_date < today: week_date = today
        
        for i in range(1, 3):
            db.session.add(ProcessInstance(
                company_id=cid, process_id=proc.id, title=f"[EXEMPLO] Rotina de Backup {i}",
                due_date=week_date, status='open', responsible_id=emp.id
            ))
            
        for i in range(1, 4):
            db.session.add(ProjectTask(
                what=f"[EXEMPLO] Sprint Task {i}", due_date=week_date,
                stage="todo", employee_id=emp.id, project_id=project.id
            ))

        guests = {user.email: user.name}
        db.session.add(Meeting(
            company_id=cid, title="[EXEMPLO] Weekly Review", scheduled_date=week_date,
            scheduled_time="11:00", guests_json=json.dumps(guests), status='draft'
        ))
        db.session.add(Meeting(
            company_id=cid, title="[EXEMPLO] Planejamento Q3", scheduled_date=week_date + timedelta(days=1),
            scheduled_time="15:30", guests_json=json.dumps(guests), status='draft'
        ))

        db.session.commit()
        print("Dados do exemplo criados no banco.")

        # 4. Gerar e Mandar
        message = get_user_summary_report(user, date_range='week')
        if message:
            try:
                bot.send_message(user.telegram, message, parse_mode='HTML')
                print(f"Mensagem enviada com sucesso!")
            except Exception as e:
                print(f"ERRO ao enviar: {e}")
        else:
            print("ERRO: Nenhum resumo gerado.")

if __name__ == "__main__":
    run_test()
