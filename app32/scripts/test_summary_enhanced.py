import os
import sys
import json
from datetime import datetime, date, timedelta

# Setup paths
sys.path.append(os.getcwd())

from app import create_app
from models import db, User, Employee, Company, Project, ProjectTask
from models.meeting import Meeting
from services.proactive_service import get_user_summary_report

def sync_sequences(db):
    """Sincroniza as sequências do Postgres"""
    tables = ['projects', 'project_tasks', 'companies', 'users', 'employees', 'meetings']
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
        
        # 1. Encontrar usuário
        user = User.query.filter(User.telegram.isnot(None)).first()
        if not user:
            print("ERRO: Nenhum usuário com Telegram encontrado.")
            return
        
        print(f"Testando para: {user.name} (Email: {user.email})")

        # 2. Get Employee
        emp = Employee.query.filter_by(user_id=user.id, status='active').first()
        if not emp:
            print("ERRO: Usuário sem vínculo ativo.")
            return

        company = Company.query.get(emp.company_id)
        
        # 3. Create Meeting for Today
        # Clean existing test meetings
        Meeting.query.filter(Meeting.title.ilike('%TESTE%')).delete()
        
        guests = {user.email: user.name, "outro@teste.com": "Outro"}
        
        today_meeting = Meeting(
            company_id=company.id,
            title="[TESTE] Reunião de Alinhamento MCP",
            scheduled_date=date.today(),
            scheduled_time="14:00",
            guests_json=json.dumps(guests),
            status='draft'
        )
        db.session.add(today_meeting)
        
        # 4. Create Meeting for Tomorrow (within the same week)
        tomorrow = date.today() + timedelta(days=1)
        future_meeting = Meeting(
            company_id=company.id,
            title="[TESTE] Reunião Estratégica Semanal",
            scheduled_date=tomorrow,
            scheduled_time="10:00",
            guests_json=json.dumps(guests),
            status='draft'
        )
        db.session.add(future_meeting)
        
        # 5. Add a project task for today
        project = Project.query.filter_by(company_id=company.id).first()
        if not project:
            project = Project(name="Projeto VIP", company_id=company.id, status='active')
            db.session.add(project)
            db.session.flush()
            
        task_today = ProjectTask(
            what="Finalizar Documentação IA",
            due_date=date.today(),
            stage="todo",
            employee_id=emp.id,
            project_id=project.id
        )
        db.session.add(task_today)
        
        db.session.commit()
        print("Dados de teste (reuniões e tarefas) criados.")

        # 6. Test Daily Summary
        print("\n--- TESTE: RESUMO DE HOJE ---")
        summary_today = get_user_summary_report(user, date_range='today')
        if summary_today:
            # Clean for console printing (REMOVE EMOJIS FOR WINDOWS CONSOLE)
            clean_msg = summary_today.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            clean_msg = clean_msg.encode('ascii', 'ignore').decode('ascii')
            print(clean_msg)
        else:
            print("Nenhum resumo gerado para hoje.")

        # 7. Test Weekly Summary
        print("\n--- TESTE: RESUMO DA SEMANA ---")
        summary_week = get_user_summary_report(user, date_range='week')
        if summary_week:
            clean_msg = summary_week.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            clean_msg = clean_msg.encode('ascii', 'ignore').decode('ascii')
            print(clean_msg)
        else:
            print("Nenhum resumo gerado para a semana.")

if __name__ == "__main__":
    run_test()
