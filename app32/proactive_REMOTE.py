import logging
import html
from datetime import datetime, date, timedelta
from models import db, User, Employee
from models.project import ProjectTask, ProjectActivityCollaborator
from models.process import ProcessInstance, ProcessInstanceCollaborator
from models.meeting import Meeting
from models.company import Company
from models.agent_action import AgentAction
from api.webhooks.telegram_webhook import bot

logger = logging.getLogger(__name__)

def get_user_summary_report(user, date_range='today'):
    """
    Gera o relatório de resumo (hoje ou semanal) para um usuário específico.
    """
    today = date.today()
    
    if date_range == 'week':
        # Domingo a Sábado
        start_date = today - timedelta(days=(today.weekday() + 1) % 7)
        end_date = start_date + timedelta(days=6)
        range_label = f"desta semana ({start_date.strftime('%d/%m')} a {end_date.strftime('%d/%m')})"
    else:
        start_date = today
        end_date = today
        range_label = "de hoje"

    # Get employee records
    employees = Employee.query.filter_by(user_id=user.id, status='active').all()
    employee_ids = [e.id for e in employees]
    emails = list(set([user.email] + [e.email for e in employees if e.email]))
    names = list(set([user.name] + [e.name for e in employees if e.name]))
    
    if not employee_ids:
        return None

    # 1. Fetch Project Tasks
    tasks_resp = ProjectTask.query.filter(
        ProjectTask.employee_id.in_(employee_ids),
        ProjectTask.stage != 'completed'
    ).all()
    
    tasks_coll_ids = [c.activity_id for c in ProjectActivityCollaborator.query.filter(
        ProjectActivityCollaborator.employee_id.in_(employee_ids),
        ProjectActivityCollaborator.is_deleted == False
    ).all()]
    
    tasks_coll = ProjectTask.query.filter(
        ProjectTask.id.in_(tasks_coll_ids),
        ProjectTask.stage != 'completed',
        ~ProjectTask.employee_id.in_(employee_ids)
    ).all()
    
    all_tasks = tasks_resp + tasks_coll

    # 2. Fetch Process Instances
    process_instances_ids = [c.process_instance_id for c in ProcessInstanceCollaborator.query.filter(
        ProcessInstanceCollaborator.employee_id.in_(employee_ids),
        ProcessInstanceCollaborator.is_deleted == False
    ).all()]
    
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
    
    all_pi = list(set(pi_direct + pi_coll))

    # 3. Fetch Meetings (where user is guest)
    meeting_q = Meeting.query.filter(Meeting.company_id.in_([e.company_id for e in employees]))
    if date_range == 'week':
        meeting_q = meeting_q.filter(Meeting.scheduled_date >= start_date, Meeting.scheduled_date <= end_date)
    else:
        meeting_q = meeting_q.filter(Meeting.scheduled_date == today)
    
    potential_meetings = meeting_q.all()
    my_meetings = []
    for m in potential_meetings:
        g_json = m.guests_json.lower() if m.guests_json else ""
        is_guest = False
        for email in emails:
            if email and email.lower() in g_json:
                is_guest = True
                break
        if not is_guest:
            for name in names:
                if name and name.lower() in g_json:
                    is_guest = True
                    break
        if is_guest:
            my_meetings.append(m)

    # 4. Fetch Pending AI Approvals
    pending_actions = AgentAction.query.filter(
        AgentAction.company_id.in_([e.company_id for e in employees]),
        AgentAction.status == 'pending'
    ).all()

    # 5. Grouping Logic
    report_data = {
        'overdue': {},
        'current_range': {}
    }
    
    all_company_ids = list(set(
        [t.project.company_id for t in all_tasks if t.project] + 
        [pi.company_id for pi in all_pi] +
        [m.company_id for m in my_meetings]
    ))
    company_map = {c.id: c for c in Company.query.filter(Company.id.in_(all_company_ids)).all()}

    def tg_clean(text):
        if not text: return ""
        return html.escape(str(text))

    # Helper to normalize date to 'date' object
    def _to_date(v):
        if not v: return None
        if isinstance(v, datetime):
             return v.date()
        return v

    # Fill Report Data - Tasks
    for t in all_tasks:
        if not t.project: continue
        cid = t.project.company_id
        d_date = _to_date(t.due_date)
        if not d_date: continue
        
        cat = None
        if d_date < today: cat = 'overdue'
        elif start_date <= d_date <= end_date: cat = 'current_range'
        
        if cat:
            if cid not in report_data[cat]: report_data[cat][cid] = {'Processos': [], 'Projetos': [], 'Reuniões': []}
            report_data[cat][cid]['Projetos'].append(f"📌 {tg_clean(t.what)} ({tg_clean(t.project_name)}) - Prazo: {d_date.strftime('%d/%m')}")

    # Fill Report Data - Processes
    for pi in all_pi:
        cid = pi.company_id
        d_date = _to_date(pi.due_date)
        if not d_date: continue
        
        cat = None
        if d_date < today: cat = 'overdue'
        elif start_date <= d_date <= end_date: cat = 'current_range'
        
        if cat:
            if cid not in report_data[cat]: report_data[cat][cid] = {'Processos': [], 'Projetos': [], 'Reuniões': []}
            report_data[cat][cid]['Processos'].append(f"⚙️ {tg_clean(pi.title)} - Prazo: {d_date.strftime('%d/%m')}")

    # Fill Report Data - Meetings
    for m in my_meetings:
        cid = m.company_id
        cat = 'current_range'
        if cid not in report_data[cat]: report_data[cat][cid] = {'Processos': [], 'Projetos': [], 'Reuniões': []}
        time_str = f" às {m.scheduled_time}" if m.scheduled_time else ""
        date_str = f" ({m.scheduled_date.strftime('%d/%m')})" if date_range == 'week' else ""
        report_data[cat][cid]['Reuniões'].append(f"🤝 <b>{tg_clean(m.title)}</b>{time_str}{date_str}")

    # 6. Build Message
    global_counter = [1]
    
    formatted_approvals = []
    for a in pending_actions[:5]:
        formatted_approvals.append(f"{global_counter[0]} - 🤖 <b>{tg_clean(a.requesting_agent.upper())}</b>: {tg_clean(a.title)}")
        global_counter[0] += 1
    
    if not any(report_data['overdue'].values()) and not any(report_data['current_range'].values()) and not formatted_approvals:
        return f"✅ <b>{tg_clean(user.name)}</b> está 100% em dia {range_label}! Nenhuma tarefa, processo ou reunião pendente encontrada para o período."

    message = f"Olá, {tg_clean(user.name)}! ☀️\n\nSou o Sapiens e trouxe seu resumo {range_label}:\n\n"
    
    if formatted_approvals:
        message += "⚖️ <b>AGUARDANDO SUA APROVAÇÃO (IA):</b>\n"
        message += "\n".join(formatted_approvals) + "\n"
        if len(pending_actions) > 5:
            message += f"...e mais {len(pending_actions) - 5} solicitações.\n"
        message += "<i>Responda 'Aprovar' ou 'Recusar' no chat do sistema.</i>\n\n"

    def format_group(section_items, current_msg_len):
        group_msg = ""
        sorted_cids = sorted(section_items.keys())
        for cid in sorted_cids:
            if current_msg_len + len(group_msg) > 3500:
                group_msg += "<i>...resumo truncado devido ao volume.</i>\n"
                break
            comp = company_map.get(cid)
            c_name = tg_clean(comp.name) if comp else f"Empresa {cid}"
            c_code = tg_clean(comp.client_code) if comp and comp.client_code else "---"
            
            for source in ['Reuniões', 'Processos', 'Projetos']:
                items = section_items[cid].get(source, [])
                if items:
                    group_msg += f" 🔹 {c_code} - {c_name} ({source})\n"
                    # Numbered items
                    for item_str in items[:7]:
                        group_msg += f"{global_counter[0]} - {item_str}\n"
                        global_counter[0] += 1
                        
                    if len(items) > 7:
                        group_msg += f"...e mais {len(items) - 7} itens.\n"
                    group_msg += "\n"
        return group_msg

    if report_data['overdue']:
        message += "🔴 <b>CRÍTICO (Atrasados):</b>\n"
        message += format_group(report_data['overdue'], len(message))
    
    if report_data['current_range']:
        label = "ENTREGA/REUNIÕES HOJE" if date_range == 'today' else "ESTA SEMANA"
        if len(message) < 3500:
            message += f"🟡 <b>{label}:</b>\n"
            message += format_group(report_data['current_range'], len(message))
    
    message += "\nEscolha um item da lista e me diga o que fazer, exemplo:\n"
    message += "20 - Alterar prazo de vencimento para 20/03/2026\n\n"
    message += "Estou à disposição para ajudar você a alcançar seus objetivos hoje. O que vamos priorizar?"
    return message

def send_morning_summaries(app):
    """
    Scans all users with a Telegram ID and sends a morning summary.
    """
    with app.app_context():
        logger.info("🌤️ Iniciando envio de resumos matinais proativos...")
        users = User.query.filter(User.telegram.isnot(None), User.is_active == True).all()
        for user in users:
            try:
                message = get_user_summary_report(user, date_range='today')
                if message:
                    logger.info(f"Enviando resumo matinal para {user.name} ({len(message)} chars)")
                    bot.send_message(user.telegram, message, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Erro ao enviar resumo para usuário {user.id}: {e}")

def notify_task_completion(app, task, completed_by_user):
    """
    Notifica o gestor quando uma tarefa é concluída via IA.
    """
    with app.app_context():
        try:
            from models import Project, Company, Employee, User
            project = Project.query.get(task.project_id)
            if not project: return
            
            manager_employee = Employee.query.get(project.manager_id) if project.manager_id else None
            manager_user = User.query.get(manager_employee.user_id) if manager_employee else None
            
            recipients = []
            if manager_user and manager_user.telegram:
                recipients.append(manager_user)
            else:
                admins = User.query.join(Employee).filter(
                    Employee.company_id == task.company_id,
                    User.telegram.isnot(None),
                    Employee.role_id == 1
                ).all()
                recipients.extend(admins)

            if not recipients: return

            msg = (
                f"✅ <b>ATIVIDADE CONCLUÍDA VIA IA</b>\n\n"
                f"Olá! Informo que a seguinte atividade foi finalizada no sistema:\n\n"
                f"📌 <b>Tarefa:</b> {html.escape(task.what)}\n"
                f"🏢 <b>Empresa:</b> {html.escape(Company.query.get(task.company_id).name)}\n"
                f"👤 <b>Executado por:</b> {html.escape(completed_by_user.name)} (via IA)\n\n"
                f"O status já foi atualizado no dashboard."
            )

            for admin in recipients:
                try:
                    bot.send_message(admin.telegram, msg, parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação para {admin.name}: {e}")
        except Exception as e:
            logger.error(f"Falha ao processar notificação de conclusão: {e}")
