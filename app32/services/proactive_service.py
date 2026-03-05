import logging
import html
import re
import inspect
import unicodedata
from datetime import datetime, date, timedelta
from sqlalchemy import func
from models import db, User, Employee
from models.project import ProjectTask, ProjectActivityCollaborator
from models.process import ProcessInstance, ProcessInstanceCollaborator
from models.meeting import Meeting
from models.company import Company
from models.agent_action import AgentAction
from api.webhooks.telegram_webhook import bot

logger = logging.getLogger(__name__)
EMAIL_FALLBACK_SUFFIX = "Registros acima da capacidade deste canal, quer que eu te envie por e-mail?"
EMAIL_FALLBACK_FRAGMENT = "Registros acima da capacidade deste canal"


def _format_my_work_report_compat(report_formatter, **kwargs):
    formatter = getattr(report_formatter, "_format_my_work_report")
    try:
        params = inspect.signature(formatter).parameters
        accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if accepts_var_kw:
            return formatter(**kwargs)

        filtered_kwargs = {k: v for k, v in kwargs.items() if k in params}
        return formatter(**filtered_kwargs)
    except Exception:
        legacy_kwargs = dict(kwargs)
        legacy_kwargs.pop("meetings", None)
        legacy_kwargs.pop("channel", None)
        legacy_kwargs.pop("payload", None)
        legacy_kwargs.pop("user_id", None)
        return formatter(**legacy_kwargs)

def get_user_summary_report(user, date_range='today', channel='telegram'):
    """
    Gera o relatório de resumo para um usuário específico.
    channel:
      - telegram (padrão): mensagem compacta e com truncamento de segurança do canal
      - email: texto completo sem truncamento
      - whatsapp/web: texto completo sem truncamento
    """
    from src.intelligence import menu_engine as report_formatter
    normalized_channel = str(channel or "telegram").strip().lower()

    today = date.today()
    start_date, end_date, range_label = _resolve_summary_period(date_range=date_range, today=today)

    user_employees = Employee.query.filter_by(user_id=user.id, status='active').all()
    employee_ids = [e.id for e in user_employees if e.id]
    company_ids = sorted({e.company_id for e in user_employees if e.company_id})
    emails = sorted({str(user.email or "").strip(), *[str(e.email or "").strip() for e in user_employees if e.email]})
    names = sorted({str(user.name or "").strip(), *[str(e.name or "").strip() for e in user_employees if e.name]})
    emails = [e for e in emails if e]
    names = [n for n in names if n]

    if not employee_ids:
        return None

    companies = Company.query.filter(Company.id.in_(company_ids)).all() if company_ids else []
    company_map = {c.id: c for c in companies}

    # 1) Atividades de Projeto (responsável direto + colaborador)
    tasks_direct = ProjectTask.query.filter(
        ProjectTask.employee_id.in_(employee_ids),
        ProjectTask.stage != 'completed'
    ).all()

    collaborator_task_ids = {
        c.activity_id
        for c in ProjectActivityCollaborator.query.filter(
            ProjectActivityCollaborator.employee_id.in_(employee_ids),
            ProjectActivityCollaborator.is_deleted == False
        ).all()
        if c.activity_id
    }
    tasks_collab = ProjectTask.query.filter(
        ProjectTask.id.in_(collaborator_task_ids),
        ProjectTask.stage != 'completed',
        ~ProjectTask.employee_id.in_(employee_ids)
    ).all() if collaborator_task_ids else []

    project_tasks = list({t.id: t for t in (tasks_direct + tasks_collab)}.values())

    # 2) Instâncias de Processo (dono/responsável/executor + colaborador)
    collaborator_instance_ids = {
        c.process_instance_id
        for c in ProcessInstanceCollaborator.query.filter(
            ProcessInstanceCollaborator.employee_id.in_(employee_ids),
            ProcessInstanceCollaborator.is_deleted == False
        ).all()
        if c.process_instance_id
    }

    process_direct = ProcessInstance.query.filter(
        db.or_(
            ProcessInstance.responsible_id.in_(employee_ids),
            ProcessInstance.executor_id.in_(employee_ids),
            ProcessInstance.owner_employee_id.in_(employee_ids)
        ),
        ProcessInstance.status != 'completed'
    ).all()
    process_collab = ProcessInstance.query.filter(
        ProcessInstance.id.in_(collaborator_instance_ids),
        ProcessInstance.status != 'completed'
    ).all() if collaborator_instance_ids else []

    process_instances = list({p.id: p for p in (process_direct + process_collab)}.values())

    owner_ids = {
        getattr(p, "owner_employee_id", None) for p in process_instances
    } | {
        getattr(p, "responsible_id", None) for p in process_instances
    } | {
        getattr(p, "executor_id", None) for p in process_instances
    }
    owner_ids = {oid for oid in owner_ids if oid}
    owner_lookup = {}
    if owner_ids:
        owner_lookup = {e.id: e.name for e in Employee.query.filter(Employee.id.in_(owner_ids)).all()}

    # 3) Reuniões Agendadas (usuário convidado)
    meetings_q = Meeting.query.filter(
        Meeting.company_id.in_(company_ids),
        func.lower(func.coalesce(Meeting.status, "")) != "completed",
        Meeting.scheduled_date.isnot(None),
    )
    potential_meetings = meetings_q.all()
    meetings = [
        m for m in potential_meetings
        if _is_meeting_for_user(m, emails=emails, names=names)
    ]

    # 4) Aprovações pendentes
    pending_actions = AgentAction.query.filter(
        AgentAction.company_id.in_(company_ids),
        AgentAction.status.in_(["pending", "awaiting_approval"])
    ).order_by(AgentAction.created_at.asc()).all()

    overdue_tasks, range_tasks = [], []
    overdue_processes, range_processes = [], []
    overdue_meetings, range_meetings = [], []

    # Normalização para o padrão "Código + Nome"
    for task in project_tasks:
        if not task.project:
            continue
        due_date = _coerce_date(task.due_date)
        if not due_date:
            continue

        company = company_map.get(task.project.company_id)
        company_code = (company.client_code if company and company.client_code else "CP")
        company_name = (company.name if company and company.name else f"Empresa {task.project.company_id}")
        project_code = f"{company_code}.J.{task.project.id}"
        task_item = {
            "company_id": task.project.company_id,
            "company_code": company_code,
            "company_name": company_name,
            "project_code": project_code,
            "project_name": task.project.name,
            "activity_code": f"{project_code}.{task.id}",
            "title": task.what,
            "responsible": task.employee.name if task.employee and task.employee.name else (task.who or "Sem responsavel"),
            "due_date": due_date.isoformat(),
            "completion_date": "-",
        }
        if due_date < today:
            overdue_tasks.append(task_item)
        elif start_date <= due_date <= end_date:
            range_tasks.append(task_item)

    for instance in process_instances:
        due_date = _coerce_date(instance.due_date)
        if not due_date:
            continue
        company = company_map.get(instance.company_id)
        company_code = (company.client_code if company and company.client_code else "CP")
        company_name = (company.name if company and company.name else f"Empresa {instance.company_id}")
        process_name = instance.process_rel.name if instance.process_rel and instance.process_rel.name else "Sem nome"
        process_code = instance.process_rel.code if instance.process_rel and instance.process_rel.code else f"{company_code}.C.{instance.process_id}"
        owner_name = _resolve_process_owner_name(instance, owner_lookup)
        item = {
            "company_id": instance.company_id,
            "company_code": company_code,
            "company_name": company_name,
            "process_code": process_code,
            "process_name": process_name,
            "instance_code": instance.instance_code or f"{process_code}.{instance.id}",
            "title": instance.title or process_name,
            "owner": owner_name,
            "due_date": due_date.isoformat(),
            "completion_date": "-",
        }
        if due_date < today:
            overdue_processes.append(item)
        elif start_date <= due_date <= end_date:
            range_processes.append(item)

    for meeting in meetings:
        scheduled_date = _coerce_date(meeting.scheduled_date)
        if not scheduled_date:
            continue
        company = company_map.get(meeting.company_id)
        company_code = (company.client_code if company and company.client_code else "CP")
        company_name = (company.name if company and company.name else f"Empresa {meeting.company_id}")
        project_code = f"{company_code}.J.{meeting.project.id}" if meeting.project else "-"
        project_name = meeting.project.name if meeting.project else "Sem projeto vinculado"
        item = {
            "company_id": meeting.company_id,
            "company_code": company_code,
            "company_name": company_name,
            "meeting_code": f"{company_code}.R.{meeting.id}",
            "meeting_name": meeting.title or f"Reuniao {meeting.id}",
            "project_code": project_code,
            "project_name": project_name,
            "scheduled_time": meeting.scheduled_time or "-",
            "due_date": scheduled_date.isoformat(),
            "completion_date": "-",
        }
        if scheduled_date < today:
            overdue_meetings.append(item)
        elif start_date <= scheduled_date <= end_date:
            range_meetings.append(item)

    has_overdue = bool(overdue_tasks or overdue_processes or overdue_meetings)
    has_period = bool(range_tasks or range_processes or range_meetings)
    has_approvals = bool(pending_actions)

    if not has_overdue and not has_period and not has_approvals:
        if normalized_channel == "email":
            return (
                f"✅ {user.name}, você está 100% em dia {range_label}.\n"
                "Nenhuma tarefa, processo ou reunião pendente foi encontrada para o período."
            )
        return (
            f"✅ {user.name} está 100% em dia {range_label}! "
            "Nenhuma tarefa, processo ou reunião pendente encontrada para o período."
        )

    sections = []

    if has_approvals:
        approval_lines = ["⚖️ APROVAÇÕES PENDENTES (IA):"]
        for idx, action in enumerate(pending_actions[:5], start=1):
            agent = (action.requesting_agent or "agente").upper()
            approval_lines.append(f"{idx}. {agent} - {action.title}")
        if len(pending_actions) > 5:
            approval_lines.append(f"...e mais {len(pending_actions) - 5} solicitações.")
        if normalized_channel == "email":
            approval_lines.append("Acesse o chat do sistema para aprovar ou recusar as solicitações.")
        else:
            approval_lines.append("Responda 'Aprovar' ou 'Recusar' no chat do sistema.")
        sections.append("\n".join(approval_lines))

    if has_overdue:
        overdue_report = _format_my_work_report_compat(
            report_formatter,
            action="my_work.overdue",
            company_label="empresas vinculadas",
            tasks=overdue_tasks,
            processes=overdue_processes,
            meetings=overdue_meetings,
            start_date=None,
            end_date=None,
            channel=normalized_channel,
            payload={"colaborador": user.name},
            user_id=user.id,
        )
        sections.append(overdue_report)

    if has_period:
        range_report = _format_my_work_report_compat(
            report_formatter,
            action="my_work.due_range",
            company_label="empresas vinculadas",
            tasks=range_tasks,
            processes=range_processes,
            meetings=range_meetings,
            start_date=start_date,
            end_date=end_date,
            channel=normalized_channel,
            payload={"colaborador": user.name},
            user_id=user.id,
        )
        sections.append(range_report)

    if normalized_channel == "email":
        intro = (
            f"Olá, {user.name}! ☀️\n"
            f"Sou o Sapiens e este é o seu resumo {range_label}.\n"
        )
        outro = "\n\nConte comigo para priorizar o próximo passo da sua agenda."
    else:
        intro = f"Olá, {user.name}! ☀️\nSou o Sapiens e trouxe seu resumo {range_label}.\n"
        outro = "\n\nEstou à disposição para ajudar você a priorizar o próximo passo."

    message = intro + "\n\n".join(sections)
    message += outro

    if normalized_channel == "telegram":
        return _truncate_telegram_message(message)
    return message


def get_user_summary_email_payload(user, date_range='today'):
    """
    Gera payload pronto para envio de e-mail do resumo do usuário.
    Retorna dict com subject, body (texto) e html_body (estilizado).
    """
    today = date.today()
    _, _, range_label = _resolve_summary_period(date_range=date_range, today=today)
    body = get_user_summary_report(user, date_range=date_range, channel='email')
    if not body:
        return None

    subject = _build_summary_email_subject(user_name=user.name, date_range=date_range, today=today)
    html_body = _render_summary_email_html(
        user_name=user.name,
        range_label=range_label,
        body_text=body,
        generated_at=today.strftime("%d/%m/%Y"),
    )
    return {
        "subject": subject,
        "body": body,
        "html_body": html_body,
    }


def _build_summary_email_subject(user_name: str, date_range: str, today: date) -> str:
    normalized = str(date_range or "today").strip().lower()
    if normalized in {"today", "hoje"}:
        return f"Resumo Diário de Atividades - {user_name} ({today.strftime('%d/%m/%Y')})"
    if normalized in {"week", "this_week", "esta semana", "esta_semana"}:
        return f"Resumo Semanal de Atividades - {user_name}"
    if normalized in {"month", "this_month", "este_mes", "este mes", "neste_mes", "neste mes"}:
        return f"Resumo Mensal de Atividades - {user_name}"
    return f"Resumo de Atividades - {user_name}"


def _render_summary_email_html(user_name: str, range_label: str, body_text: str, generated_at: str) -> str:
    safe_user = html.escape(str(user_name or "Colaborador"))
    safe_range = html.escape(str(range_label or "de hoje"))
    safe_generated_at = html.escape(str(generated_at or ""))
    body_html = _render_summary_body_html(body_text or "")

    return f"""
<!doctype html>
<html lang="pt-BR">
  <body style="margin:0;padding:0;background:#f5f7fb;font-family:Segoe UI,Arial,sans-serif;color:#0f172a;">
    <div style="max-width:920px;margin:24px auto;padding:0 14px;">
      <div style="background:linear-gradient(135deg,#0f172a 0%,#1d4ed8 55%,#2563eb 100%);color:#fff;border-radius:16px;padding:24px 28px;box-shadow:0 8px 22px rgba(15,23,42,.20);">
        <div style="font-size:11px;opacity:.95;letter-spacing:.8px;text-transform:uppercase;font-weight:700;">Sapiens • Versus Gestão Corporativa</div>
        <h1 style="margin:10px 0 6px;font-size:25px;line-height:1.25;font-weight:800;">Resumo de atividades {safe_range}</h1>
        <div style="font-size:14px;opacity:.98;line-height:1.5;">
          Colaborador: <strong>{safe_user}</strong><br>
          Data base: <strong>{safe_generated_at}</strong>
        </div>
      </div>

      <div style="background:#ffffff;border:1px solid #dbe3ef;border-radius:16px;padding:22px 24px;margin-top:14px;line-height:1.65;">
        {body_html}
      </div>

      <div style="background:#ffffff;border:1px solid #dbe3ef;border-radius:16px;padding:18px 24px;margin-top:14px;">
        <div style="font-size:16px;font-weight:800;color:#0f172a;">Sapiens Versus</div>
        <div style="font-size:14px;color:#1e3a8a;font-weight:700;margin-top:2px;">Versus Gestão Corporativa</div>
        <div style="font-size:13px;color:#334155;margin-top:8px;">
          E-mail:
          <a href="mailto:sapiens@gestaoversus.com.br" style="color:#1d4ed8;text-decoration:none;">sapiens@gestaoversus.com.br</a>
        </div>
        <div style="font-size:13px;color:#334155;margin-top:4px;">Telefone: 71 9 8238-5225</div>
        <div style="margin-top:14px;">
          <img src="cid:versus_signature_logo" alt="Versus Gestão Corporativa" style="max-width:280px;width:100%;height:auto;display:block;border:0;">
        </div>
      </div>

      <div style="text-align:center;color:#64748b;font-size:12px;margin:14px 0 6px;">
        Mensagem automática enviada pelo Sapiens.
      </div>
    </div>
  </body>
</html>
"""


def _render_summary_body_html(body_text: str) -> str:
    lines = str(body_text or "").splitlines()
    parts = []
    current_section = None
    expect_company_name = False

    def _norm(text: str) -> str:
        normalized = unicodedata.normalize("NFD", str(text or "").lower().strip())
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    section_styles = {
        "projetos": {
            "label": "Projetos",
            "color": "#1d4ed8",
            "bg": "#eff6ff",
            "icon": "📁",
        },
        "processos": {
            "label": "Processos",
            "color": "#7c3aed",
            "bg": "#f5f3ff",
            "icon": "⚙️",
        },
        "reunioes": {
            "label": "Reuniões",
            "color": "#0f766e",
            "bg": "#ecfeff",
            "icon": "🤝",
        },
    }

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            parts.append("<div style='height:8px;'></div>")
            continue

        stripped = line.strip()
        lowered = stripped.lower()

        if lowered.startswith("olá,") or lowered.startswith("ola,"):
            parts.append(
                f"<div style='font-size:17px;font-weight:800;color:#0f172a;margin:0 0 8px;'>{html.escape(stripped)}</div>"
            )
            continue

        if lowered.startswith("sou o sapiens"):
            parts.append(
                f"<div style='font-size:14px;color:#334155;margin:0 0 10px;'>{html.escape(stripped)}</div>"
            )
            continue

        if "aprovações pendentes" in lowered or "aprovacoes pendentes" in lowered:
            parts.append(
                f"<div style='margin:10px 0 8px;padding:8px 12px;border-left:4px solid #f59e0b;background:#fffbeb;color:#92400e;font-size:13px;font-weight:800;border-radius:8px;'>{html.escape(stripped)}</div>"
            )
            continue

        if lowered.startswith("resumo das atividades"):
            parts.append(
                f"<div style='margin:10px 0 8px;padding:8px 12px;border-left:4px solid #2563eb;background:#eff6ff;color:#1e3a8a;font-size:13px;font-weight:800;border-radius:8px;'>{html.escape(stripped)}</div>"
            )
            continue

        normalized_label = _norm(stripped)
        if normalized_label == "empresa":
            expect_company_name = True
            current_section = None
            continue

        if expect_company_name and line.startswith("- "):
            company_name = html.escape(line[2:].strip())
            parts.append(
                "<div style='margin:12px 0 8px;padding:10px 14px;border:1px solid #dbeafe;"
                "border-left:5px solid #1d4ed8;border-radius:12px;background:#f8fbff;'>"
                "<div style='font-size:11px;font-weight:800;color:#1e3a8a;letter-spacing:.6px;"
                "text-transform:uppercase;margin-bottom:3px;'>Empresa</div>"
                f"<div style='font-size:16px;font-weight:800;color:#0f172a;'>{company_name}</div>"
                "</div>"
            )
            expect_company_name = False
            continue

        section_key = None
        if normalized_label == "projetos":
            section_key = "projetos"
        elif normalized_label == "processos":
            section_key = "processos"
        elif normalized_label in {"reunioes agendadas", "reunioes"}:
            section_key = "reunioes"

        if section_key:
            current_section = section_key
            style = section_styles[section_key]
            parts.append(
                f"<div style='margin:7px 0 6px 22px;padding:6px 10px;background:{style['bg']};"
                f"border-left:4px solid {style['color']};border-radius:8px;font-size:14px;"
                f"font-weight:800;color:{style['color']};'>{style['icon']} {style['label']}</div>"
            )
            continue

        if line.startswith("  - "):
            content_raw = line[4:].strip()
            content_norm = _norm(content_raw)

            if current_section == "projetos" and content_norm.startswith("atividades"):
                content_raw = "Atividade de Projetos"
            elif current_section == "processos" and content_norm.startswith("instancias"):
                content_raw = "Instância de Processos"
            elif current_section == "reunioes" and content_norm.startswith("reunioes"):
                content_raw = "Agendamento de Reuniões"

            content = html.escape(content_raw)
            section_color = section_styles[current_section]["color"] if current_section else "#334155"
            parts.append(
                f"<div style='margin:4px 0 4px 44px;font-size:12.5px;font-weight:700;color:{section_color};'>"
                f"• {content}</div>"
            )
            continue

        if line.startswith("- "):
            content = html.escape(line[2:].strip())
            if current_section:
                if current_section == "reunioes":
                    section_color = section_styles[current_section]["color"]
                    parts.append(
                        f"<div style='margin:4px 0 4px 64px;padding:7px 10px;background:#f8fafc;"
                        f"border-left:3px solid {section_color};border-radius:8px;font-size:13px;color:#1e293b;'>"
                        f"{content}</div>"
                    )
                else:
                    section_color = section_styles[current_section]["color"]
                    parts.append(
                        f"<div style='margin:4px 0 4px 44px;font-size:13.5px;font-weight:700;color:{section_color};'>"
                        f"{content}</div>"
                    )
                continue

            parts.append(
                f"<div style='margin:4px 0 4px 8px;font-size:14px;color:#0f172a;'>• {content}</div>"
            )
            continue

        if line.startswith("    - "):
            content = html.escape(line[6:].strip())
            section_color = section_styles[current_section]["color"] if current_section else "#334155"
            parts.append(
                f"<div style='margin:4px 0 4px 64px;padding:7px 10px;background:#f8fafc;"
                f"border-left:3px solid {section_color};border-radius:8px;font-size:13px;color:#1e293b;'>"
                f"{content}</div>"
            )
            continue

        if re.match(r"^\d+\.\s", stripped):
            parts.append(
                f"<div style='margin:4px 0 4px 8px;font-size:14px;color:#0f172a;font-weight:600;'>{html.escape(stripped)}</div>"
            )
            continue

        parts.append(
            f"<div style='margin:4px 0;font-size:14px;color:#1f2937;'>{html.escape(stripped)}</div>"
        )

    return "".join(parts)


def _resolve_summary_period(date_range: str, today: date) -> tuple[date, date, str]:
    raw = str(date_range or "today").strip()
    normalized = raw.lower().strip()

    if normalized in {"today", "hoje"}:
        return today, today, f"de hoje ({today.strftime('%d/%m/%Y')})"

    if normalized in {"week", "this_week", "esta semana", "esta_semana"}:
        end = today + timedelta(days=6)
        return today, end, f"da semana ({today.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')})"

    if normalized in {"month", "this_month", "este_mes", "este mes", "neste_mes", "neste mes"}:
        first_next = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        end = first_next - timedelta(days=1)
        return today, end, f"deste mês ({today.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')})"

    if normalized in {"next_15_days", "proximos_15_dias", "proximos 15 dias", "próximos 15 dias"}:
        end = today + timedelta(days=14)
        return today, end, f"dos próximos 15 dias ({today.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')})"

    custom = _parse_custom_period(raw)
    if custom:
        start, end = custom
        return start, end, f"do período ({start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')})"

    # Fallback seguro: hoje
    return today, today, f"de hoje ({today.strftime('%d/%m/%Y')})"


def _parse_custom_period(raw: str):
    if not raw:
        return None

    tokens = []
    for match in raw.replace(" até ", " a ").replace(" ate ", " a ").split(" a "):
        val = _coerce_date(match.strip())
        if val:
            tokens.append(val)

    if len(tokens) == 2:
        start, end = tokens
        return (start, end) if start <= end else (end, start)

    return None


def _coerce_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    raw = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _is_meeting_for_user(meeting, emails, names) -> bool:
    guests_raw = (meeting.guests_json or "").lower()
    if not guests_raw:
        return False

    for email_value in emails:
        if email_value and email_value.lower() in guests_raw:
            return True

    for name_value in names:
        if name_value and name_value.lower() in guests_raw:
            return True

    return False


def _resolve_process_owner_name(instance, owner_lookup: dict) -> str:
    for field in ("owner_employee_id", "responsible_id", "executor_id"):
        emp_id = getattr(instance, field, None)
        if emp_id and owner_lookup.get(emp_id):
            return owner_lookup[emp_id]
    return "Sem dono definido"


def _truncate_telegram_message(message: str, max_chars: int = 3900) -> str:
    if len(message or "") <= max_chars:
        return message
    suffix = f"\n\n{EMAIL_FALLBACK_SUFFIX}"
    safe_limit = max_chars - len(suffix)
    clipped = (message or "")[: max(0, safe_limit)].rstrip()
    return f"{clipped}{suffix}"


def _normalize_confirmation_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").strip())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.lower().split())


def _is_affirmative_email_confirmation(text: str) -> bool:
    normalized = _normalize_confirmation_text(text)
    if not normalized:
        return False

    direct_hits = {
        "sim",
        "s",
        "ok",
        "claro",
        "pode",
        "pode sim",
        "envia",
        "envie",
        "manda",
        "quero",
    }
    if normalized in direct_hits:
        return True

    keyword_hits = (
        "por email",
        "por e-mail",
        "pode enviar",
        "envie por",
        "manda por",
        "quero por",
    )
    return any(keyword in normalized for keyword in keyword_hits)


def _infer_date_range_from_summary_text(content: str) -> str:
    normalized = _normalize_confirmation_text(content)
    if "da semana (" in normalized:
        return "week"
    if "deste mes (" in normalized:
        return "month"
    if "proximos 15 dias (" in normalized:
        return "next_15_days"

    match = re.search(r"(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})", content or "")
    if match:
        return f"{match.group(1)} a {match.group(2)}"

    return "today"


def _find_recent_email_offer_message(user_id: int, company_id: int, channel: str = "telegram", lookback_minutes: int = 1440):
    from models.agent_message import AgentMessage

    cutoff = datetime.utcnow() - timedelta(minutes=lookback_minutes)
    return AgentMessage.query.filter(
        AgentMessage.user_id == user_id,
        AgentMessage.company_id == company_id,
        AgentMessage.channel == channel,
        AgentMessage.direction == "outbound",
        AgentMessage.created_at >= cutoff,
        AgentMessage.content.ilike(f"%{EMAIL_FALLBACK_FRAGMENT}%"),
    ).order_by(AgentMessage.created_at.desc()).first()


def try_handle_summary_email_confirmation(user, company_id: int, incoming_text: str, channel: str = "telegram"):
    """
    Fluxo rápido para confirmação via Telegram:
    quando o usuário responde "sim" após resumo truncado, dispara o envio por e-mail.
    """
    if channel != "telegram" or not user or not company_id:
        return False, None

    if not _is_affirmative_email_confirmation(incoming_text):
        return False, None

    offer_message = _find_recent_email_offer_message(
        user_id=user.id,
        company_id=company_id,
        channel=channel,
    )
    if not offer_message:
        return False, None

    user_email = str(getattr(user, "email", "") or "").strip()
    if not user_email:
        return True, "Não consegui enviar por e-mail porque seu cadastro não possui um e-mail válido."

    metadata = offer_message.metadata_json or {}
    date_range = str(metadata.get("summary_date_range") or "").strip() or _infer_date_range_from_summary_text(offer_message.content)

    payload = get_user_summary_email_payload(user, date_range=date_range)
    if not payload:
        return True, "Não consegui gerar o resumo completo para envio por e-mail agora."

    from services.email_service import email_service

    sent = email_service.send_email(
        to_emails=[user_email],
        subject=payload["subject"],
        body=payload["body"],
        html_body=payload.get("html_body"),
    )
    if sent:
        return True, f"Perfeito, {user.name}! ✅\nEnviei o resumo completo para {user_email}."

    return True, "Tentei enviar o e-mail, mas houve uma falha no serviço agora. Posso tentar novamente."


def _log_summary_agent_message(user, company_id: int, chat_id: str, message: str, date_range: str):
    try:
        from models.agent_message import AgentMessage

        db.session.add(AgentMessage(
            company_id=company_id,
            user_id=user.id,
            agent_type='work_agent_squad',
            agent_name='sapiens',
            direction='outbound',
            channel='telegram',
            content=message,
            metadata_json={
                "thread_id": f"tg_{chat_id}",
                "contact": "sapiens",
                "telegram_id": str(chat_id),
                "summary_date_range": date_range,
                "email_offer_available": EMAIL_FALLBACK_FRAGMENT in (message or ""),
            }
        ))
        db.session.commit()
    except Exception as log_err:
        db.session.rollback()
        logger.warning("Falha ao registrar AgentMessage do resumo proativo: %s", log_err)

def send_morning_summaries(app):
    """
    Scans all users with a Telegram ID and sends a morning summary.
    """
    if not bot:
        logger.warning("Bot Telegram indisponível: resumo matinal não será enviado.")
        return

    with app.app_context():
        logger.info("🌤️ Iniciando envio de resumos matinais proativos...")
        users = User.query.filter(
            User.is_active == True,
            User.telegram.isnot(None),
            func.trim(User.telegram) != ''
        ).all()
        for user in users:
            try:
                chat_id = (user.telegram or "").strip()
                if not chat_id:
                    logger.warning("Usuário %s sem chat_id Telegram válido; resumo ignorado.", user.id)
                    continue

                message = get_user_summary_report(user, date_range='today')
                if message:
                    logger.info(f"Enviando resumo matinal para {user.name} ({len(message)} chars)")
                    bot.send_message(chat_id, message)
                    try:
                        from src.intelligence.identity import get_best_company_id
                        summary_company_id = get_best_company_id(user)
                    except Exception:
                        summary_company_id = None

                    if summary_company_id:
                        _log_summary_agent_message(
                            user=user,
                            company_id=summary_company_id,
                            chat_id=chat_id,
                            message=message,
                            date_range='today',
                        )
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
                    func.trim(User.telegram) != '',
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
                    chat_id = (admin.telegram or "").strip()
                    if not chat_id:
                        continue
                    bot.send_message(chat_id, msg, parse_mode='HTML')
                except Exception as e:
                    logger.error(f"Erro ao enviar notificação para {admin.name}: {e}")
        except Exception as e:
            logger.error(f"Falha ao processar notificação de conclusão: {e}")
