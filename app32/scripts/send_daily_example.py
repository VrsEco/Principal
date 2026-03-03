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
        
        # 1. Encontrar usuário Fabiano (ID fixo ou primeiro com TG)
        user = User.query.filter(User.telegram == '8507771166').first()
        if not user:
            user = User.query.filter(User.telegram.isnot(None)).first()
            if not user:
                print("ERRO: Nenhum usuário com Telegram encontrado.")
                return
        
        print(f"Gerando exemplo DIÁRIO para: {user.name} (TG: {user.telegram})")

        # 2. Get Employee and Company
        emp = Employee.query.filter_by(user_id=user.id, status='active').first()
        if not emp:
            print("ERRO: Usuário sem vínculo ativo.")
            return

        cid = emp.company_id
        today = date.today()
        
        # Limpar dados de exemplo anteriores
        Meeting.query.filter(Meeting.title.ilike('%[DIARIO]%')).delete()
        ProjectTask.query.filter(ProjectTask.what.ilike('%[DIARIO]%')).delete()
        ProcessInstance.query.filter(ProcessInstance.title.ilike('%[DIARIO]%')).delete()
        AgentAction.query.filter(AgentAction.title.ilike('%[DIARIO]%')).delete()
        db.session.commit()

        # 3. Criar Itens para HOJE
        
        # Ação pendente
        db.session.add(AgentAction(
            type="business_decision", status="pending", requesting_agent="business_architect",
            title="[DIARIO] Alteração de Estrutura Organizacional", 
            description="Necessário validar antes do anúncio oficial.",
            company_id=cid, user_id=user.id
        ))

        # Processo & Projeto para vincular
        proc = Process.query.filter_by(company_id=cid).first()
        if not proc:
            proc = Process(name="Operacional Diário", company_id=cid, code="OP-DIARIO")
            db.session.add(proc)
            db.session.flush()

        project = Project.query.filter_by(company_id=cid).first()
        if not project:
            project = Project(name="Gestão 2026", company_id=cid, status='active')
            db.session.add(project)
            db.session.flush()

        # 1 Atrasado (Processo)
        db.session.add(ProcessInstance(
            company_id=cid, process_id=proc.id, title="[DIARIO] Fechamento de Caixa Anterior",
            due_date=today - timedelta(days=1), status='open', responsible_id=emp.id
        ))

        # 2 Para Hoje
        db.session.add(ProjectTask(
            what="[DIARIO] Enviar Relatório MCP", due_date=today,
            stage="todo", employee_id=emp.id, project_id=project.id
        ))
        db.session.add(ProcessInstance(
            company_id=cid, process_id=proc.id, title="[DIARIO] Check-in com Equipe",
            due_date=today, status='open', responsible_id=emp.id
        ))

        # 1 Reunião hoje
        guests = {user.email: user.name}
        db.session.add(Meeting(
            company_id=cid, title="[DIARIO] Stand-up Gestão Versus", scheduled_date=today,
            scheduled_time="10:00", guests_json=json.dumps(guests), status='draft'
        ))

        db.session.commit()
        print("Dados do exemplo DIÁRIO criados.")

        # 4. Gerar e Mandar
        message = get_user_summary_report(user, date_range='today')
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
