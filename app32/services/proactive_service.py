import logging
from datetime import datetime, date
from models import db, User, Employee
from models.project import ProjectTask, ProjectActivityCollaborator
from models.process import ProcessInstance, ProcessInstanceCollaborator
from api.webhooks.telegram_webhook import bot

logger = logging.getLogger(__name__)

def send_morning_summaries(app):
    """
    Scans all users with a Telegram ID and sends a morning summary of their tasks.
    """
    with app.app_context():
        logger.info("🌤️ Iniciando envio de resumos matinais proativos...")
        
        users = User.query.filter(User.telegram.isnot(None), User.is_active == True).all()
        
        if not users:
            logger.info("Nenhum usuário com Telegram vinculado encontrado.")
            return

        today = date.today()
        
        for user in users:
            try:
                # Get all employee records for this user (could be multiple companies)
                employees = Employee.query.filter_by(user_id=user.id, status='active').all()
                employee_ids = [e.id for e in employees]
                
                if not employee_ids:
                    continue

                # 1. Fetch Project Tasks
                # Where user is directly responsible
                tasks_resp = ProjectTask.query.filter(
                    ProjectTask.employee_id.in_(employee_ids),
                    ProjectTask.stage != 'completed'
                ).all()
                
                # Where user is collaborator
                tasks_coll_ids = [c.activity_id for c in ProjectActivityCollaborator.query.filter(
                    ProjectActivityCollaborator.employee_id.in_(employee_ids),
                    ProjectActivityCollaborator.is_deleted == False
                ).all()]
                
                tasks_coll = ProjectTask.query.filter(
                    ProjectTask.id.in_(tasks_coll_ids),
                    ProjectTask.stage != 'completed',
                    ~ProjectTask.employee_id.in_(employee_ids) # Avoid duplicates
                ).all()
                
                all_tasks = tasks_resp + tasks_coll

                # 2. Fetch Process Instances
                # Where user is owner/resp/executor in JSON or table
                process_instances_ids = [c.process_instance_id for c in ProcessInstanceCollaborator.query.filter(
                    ProcessInstanceCollaborator.employee_id.in_(employee_ids),
                    ProcessInstanceCollaborator.is_deleted == False
                ).all()]
                
                # Also check direct fields in ProcessInstance
                pi_direct = ProcessInstance.query.filter(
                    db.or_(
                        ProcessInstance.responsible_id.in_(employee_ids),
                        ProcessInstance.executor_id.in_(employee_ids),
                        ProcessInstance.owner_employee_id.in_(employee_ids)
                    ),
                    ProcessInstance.status != 'completed'
                ).all()
                
                pi_coll = ProcessInstance.query.filter(
                    ProcessInstance.id.in_(process_instances_ids),
                    ProcessInstance.status != 'completed'
                ).all()
                
                all_pi = list(set(pi_direct + pi_coll)) # Unique instances

                # 3. Categorize
                overdue = []
                due_today = []
                
                # Categorize Tasks
                for t in all_tasks:
                    d_date = t.due_date
                    if d_date:
                        if d_date < today:
                            overdue.append(f"📌 [Tarefa] {t.what} ({t.project_name}) - Prazo: {d_date.strftime('%d/%m')}")
                        elif d_date == today:
                            due_today.append(f"📌 [Tarefa] {t.what} ({t.project_name})")

                # Categorize Process Instances
                for pi in all_pi:
                    d_date = pi.due_date
                    if d_date:
                        if d_date < today:
                            overdue.append(f"⚙️ [Processo] {pi.title} - Prazo: {d_date.strftime('%d/%m')}")
                        elif d_date == today:
                            due_today.append(f"⚙️ [Processo] {pi.title}")

                # 4. Format and Send Message
                if not overdue and not due_today:
                    # Message for "Zero Tasks" - good news!
                    # msg = f"Bom dia, {user.name}! ☀️\n\nVocê não tem pendências críticas para hoje. Que tal planejar os próximos passos?"
                    # For proactive, only send if there is SOMETHING? Or always?
                    # Let's send only if there's work to do or a "weekly light" message.
                    continue

                message = f"Bom dia, {user.name}! ☀️\n\nSou o Sapiens, da Versus Gestão Corporativa, e trouxe seu resumo de hoje:\n\n"
                
                if overdue:
                    message += "🔴 *CRÍTICO (Atrasados):*\n"
                    message += "\n".join(overdue) + "\n\n"
                
                if due_today:
                    message += "🟡 *ENTREGA HOJE:*\n"
                    message += "\n".join(due_today) + "\n\n"
                
                message += "Estou à disposição para ajudar você a alcançar seus objetivos hoje. O que vamos priorizar?"
                
                # Send to Telegram
                try:
                    bot.send_message(user.telegram, message, parse_mode='Markdown')
                    logger.info(f"✅ Resumo proativo enviado para {user.name} ({user.telegram})")
                except Exception as tg_err:
                    logger.error(f"❌ Erro ao enviar Telegram para {user.name}: {tg_err}")

            except Exception as e:
                logger.error(f"Erro ao processar resumo proativo para usuário {user.id}: {e}")

def notify_task_completion(app, task, completed_by_user):
    """
    Notifies a supervisor or project owner when a task is completed.
    (Self-Healing and Proactivity Fase 4)
    """
    with app.app_context():
        # Implementation for notifying managers...
        pass
