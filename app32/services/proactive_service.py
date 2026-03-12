import logging
import html
import re
import inspect
import unicodedata
from collections import defaultdict
from datetime import datetime, date, timedelta
from sqlalchemy import func
from models import db, User, Employee
from models.project import Project, ProjectTask, ProjectActivityCollaborator
from models.process import ProcessInstance, ProcessInstanceCollaborator
from models.meeting import Meeting
from models.company import Company
from models.agent_action import AgentAction
from api.webhooks.telegram_webhook import bot
from src.core.theme_tokens import (
    get_summary_email_theme,
    get_summary_email_section_styles,
)
from utils.permissions import _normalize_role_title

logger = logging.getLogger(__name__)
EMAIL_FALLBACK_SUFFIX = "Registros acima da capacidade deste canal, quer que eu te envie por e-mail?"
EMAIL_FALLBACK_FRAGMENT = "Registros acima da capacidade deste canal"
SUMMARY_DELIVERY_CHANNELS = ("telegram", "whatsapp", "email")

DAILY_INSPIRATION_QUOTES = [
    ("O sucesso nasce do querer.", "Napoleon Hill"),
    ("O que pode ser medido pode ser melhorado.", "Peter Drucker"),
    ("Leveza também é produtividade.", "Anne Lamott"),
    ("Feito é melhor que perfeito.", "Sheryl Sandberg"),
    ("A melhor maneira de prever o futuro é criá-lo.", "Peter Drucker"),
    ("Respire. Um passo de cada vez também é avanço.", "Desmond Tutu"),
    ("Tudo parece impossível até acontecer.", "Nelson Mandela"),
    ("Simplicidade é sofisticação.", "Leonardo da Vinci"),
    ("Gentileza gera força silenciosa.", "Dalai Lama"),
    ("Comece antes de estar pronto.", "Steven Pressfield"),
    ("Quem sabe focar, avança.", "Peter Drucker"),
    ("A alegria não atrapalha a excelência.", "Maya Angelou"),
    ("Disciplina é liberdade.", "Jocko Willink"),
    ("O importante é transformar intenção em ação.", "Indra Nooyi"),
    ("Que o seu dia tenha propósito e leveza.", "Martha Medeiros"),
]


def _resolve_summary_delivery_channels(user) -> list[str]:
    raw_value = str(getattr(user, "summary_delivery_channels", "") or "").strip().lower()
    if not raw_value:
        raw_value = "telegram"

    channels = []
    for item in raw_value.split(','):
        channel = item.strip().lower()
        if channel in SUMMARY_DELIVERY_CHANNELS and channel not in channels:
            channels.append(channel)
    return channels or ["telegram"]


def _format_summary_recipient(user, channel: str) -> str | None:
    if channel == "telegram":
        return str(getattr(user, "telegram", "") or "").strip() or None
    if channel == "whatsapp":
        return str(getattr(user, "whatsapp", "") or "").strip() or None
    if channel == "email":
        return str(getattr(user, "email", "") or "").strip() or None
    return None


def _get_available_summary_channels(user) -> list[str]:
    available = []
    for channel in SUMMARY_DELIVERY_CHANNELS:
        if _format_summary_recipient(user, channel):
            available.append(channel)
    return available


def _build_summary_attempt_order(user) -> list[str]:
    preferred = _resolve_summary_delivery_channels(user)
    available = _get_available_summary_channels(user)

    ordered = []
    for channel in preferred + available:
        if channel in SUMMARY_DELIVERY_CHANNELS and channel not in ordered:
            ordered.append(channel)
    return ordered


def _build_summary_message_for_channel(user, date_range: str, channel: str) -> dict | None:
    normalized_channel = str(channel or "telegram").strip().lower()
    if normalized_channel == "email":
        return get_user_summary_email_payload(user, date_range=date_range)

    message = get_user_summary_report(user, date_range=date_range, channel=normalized_channel)
    if not message:
        return None
    return {"body": message}


def _send_summary_via_channel(user, date_range: str, channel: str) -> dict:
    normalized_channel = str(channel or "").strip().lower()
    recipient = _format_summary_recipient(user, normalized_channel)
    if not recipient:
        return {"success": False, "channel": normalized_channel, "error": "destinatário não configurado"}

    payload = _build_summary_message_for_channel(user, date_range=date_range, channel=normalized_channel)
    if not payload:
        return {"success": False, "channel": normalized_channel, "error": "resumo vazio"}

    from services.notification_hub import notification_hub

    if normalized_channel == "email":
        result = notification_hub.send_email(
            recipient,
            payload["subject"],
            payload["body"],
            html_body=payload.get("html_body"),
        )
        result["message"] = payload["body"]
        return result

    if normalized_channel == "telegram":
        result = notification_hub.send_telegram(recipient, payload["body"], parse_mode="HTML")
        result["message"] = payload["body"]
        return result

    if normalized_channel == "whatsapp":
        result = notification_hub.send_whatsapp(recipient, payload["body"])
        result["message"] = payload["body"]
        return result

    return {"success": False, "channel": normalized_channel, "error": "canal não suportado"}


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

def _normalize_summary_user_role(user, user_employees: list[Employee] | None = None) -> str:
    role = str(getattr(user, "role", "") or "").strip().lower()
    if role in {"admin", "administrator"}:
        return "admin"
    if role == "client":
        return "client"

    for employee in user_employees or []:
        role_title = _normalize_role_title(employee.role.title if employee and employee.role else None)
        if role_title in {"superuser", "administrador", "administrator", "admin"}:
            return "admin"

    return "collaborator"


def _format_date_br(value) -> str:
    due_date = _coerce_date(value)
    return due_date.strftime("%d/%m/%Y") if due_date else "-"


def _format_due_hint(due_date: date, today: date) -> str:
    if not due_date:
        return "sem data"
    if due_date < today:
        return f"atrasada desde {due_date.strftime('%d/%m')}"
    if due_date == today:
        return "vence hoje"
    if due_date == today + timedelta(days=1):
        return "vence amanhã"
    return f"vence em {due_date.strftime('%d/%m')}"


def _get_daily_inspiration(today: date) -> str:
    if not DAILY_INSPIRATION_QUOTES:
        return ""
    index = today.toordinal() % len(DAILY_INSPIRATION_QUOTES)
    quote, author = DAILY_INSPIRATION_QUOTES[index]
    return f"\"{quote}\" — {author}"


def _describe_summary_target_window(date_range: str) -> str:
    normalized = str(date_range or "today").strip().lower()
    if normalized in {"today", "hoje"}:
        return "para hoje"
    if normalized in {"week", "this_week", "esta semana", "esta_semana"}:
        return "para esta semana"
    if normalized in {"month", "this_month", "este_mes", "este mes", "neste_mes", "neste mes"}:
        return "para este mês"
    return "para o período selecionado"


def _build_task_summary_item(task, company_map: dict[int, Company], today: date):
    if not task.project:
        return None

    due_date = _coerce_date(task.due_date)
    if not due_date:
        return None

    company = company_map.get(task.project.company_id)
    company_code = (company.client_code if company and company.client_code else "CP")
    project_code = f"{company_code}.J.{task.project.id}"
    responsible = task.employee.name if task.employee and task.employee.name else (task.who or "Sem responsável")

    return {
        "kind": "task",
        "id": task.id,
        "company_id": task.project.company_id,
        "code": f"{project_code}.{task.id}",
        "title": task.what,
        "responsible": responsible,
        "due_date": due_date,
        "due_label": _format_due_hint(due_date, today),
        "group_type": "Projeto",
        "group_id": task.project.id,
        "group_label": f"{project_code} - {task.project.name}",
    }


def _build_process_summary_item(instance, company_map: dict[int, Company], owner_lookup: dict[int, str], today: date):
    due_date = _coerce_date(instance.due_date)
    if not due_date:
        return None

    company = company_map.get(instance.company_id)
    company_code = (company.client_code if company and company.client_code else "CP")
    process_name = instance.process_rel.name if instance.process_rel and instance.process_rel.name else "Sem nome"
    process_code = instance.process_rel.code if instance.process_rel and instance.process_rel.code else f"{company_code}.C.{instance.process_id}"
    owner_name = _resolve_process_owner_name(instance, owner_lookup)

    return {
        "kind": "process",
        "id": instance.id,
        "company_id": instance.company_id,
        "code": instance.instance_code or f"{process_code}.{instance.id}",
        "title": instance.title or process_name,
        "responsible": owner_name,
        "due_date": due_date,
        "due_label": _format_due_hint(due_date, today),
        "group_type": "Processo",
        "group_id": instance.process_id,
        "group_label": f"{process_code} - {process_name}",
    }


def _build_meeting_summary_item(meeting, company_map: dict[int, Company], today: date):
    due_date = _coerce_date(meeting.scheduled_date)
    if not due_date:
        return None

    company = company_map.get(meeting.company_id)
    company_code = (company.client_code if company and company.client_code else "CP")
    project_code = f"{company_code}.J.{meeting.project.id}" if meeting.project else "-"
    project_name = meeting.project.name if meeting.project else "Sem projeto vinculado"
    meeting_name = meeting.title or f"Reunião {meeting.id}"
    time_label = str(meeting.scheduled_time or "").strip()
    due_label = "hoje" if due_date == today else ("amanhã" if due_date == today + timedelta(days=1) else due_date.strftime('%d/%m'))
    if time_label:
        due_label = f"{due_label} às {time_label}"

    return {
        "kind": "meeting",
        "id": meeting.id,
        "company_id": meeting.company_id,
        "code": f"{company_code}.R.{meeting.id}",
        "title": f"Reunião — {meeting_name}",
        "responsible": "Agenda",
        "due_date": due_date,
        "due_label": due_label,
        "group_type": "Reunião",
        "group_id": meeting.id,
        "group_label": f"{project_code} - {project_name}",
    }


def _sort_summary_items(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            item.get("due_date") or date.max,
            str(item.get("responsible") or ""),
            str(item.get("title") or ""),
        ),
    )


def _build_summary_context(user, date_range: str = "today") -> dict | None:
    today = date.today()
    start_date, end_date, range_label = _resolve_summary_period(date_range=date_range, today=today)

    user_employees = Employee.query.filter_by(user_id=user.id, status='active').all()
    employee_ids = sorted({e.id for e in user_employees if e.id})
    company_ids = sorted({e.company_id for e in user_employees if e.company_id})
    role = _normalize_summary_user_role(user, user_employees)

    if role == "admin" and not company_ids:
        try:
            from src.intelligence.identity import get_best_company_id
            best_company_id = get_best_company_id(user)
        except Exception:
            best_company_id = None
        if best_company_id:
            company_ids = [best_company_id]

    if not company_ids and not employee_ids:
        return None

    companies = Company.query.filter(Company.id.in_(company_ids)).all() if company_ids else []
    company_map = {c.id: c for c in companies}
    emails = sorted({str(user.email or "").strip(), *[str(e.email or "").strip() for e in user_employees if e.email]})
    names = sorted({str(user.name or "").strip(), *[str(e.name or "").strip() for e in user_employees if e.name]})
    emails = [e for e in emails if e]
    names = [n for n in names if n]

    tasks_direct = ProjectTask.query.filter(
        ProjectTask.employee_id.in_(employee_ids),
        ProjectTask.stage != 'completed'
    ).all() if employee_ids else []

    collaborator_task_ids = {
        c.activity_id
        for c in ProjectActivityCollaborator.query.filter(
            ProjectActivityCollaborator.employee_id.in_(employee_ids),
            ProjectActivityCollaborator.is_deleted == False
        ).all()
        if c.activity_id
    } if employee_ids else set()

    tasks_collab = ProjectTask.query.filter(
        ProjectTask.id.in_(collaborator_task_ids),
        ProjectTask.stage != 'completed',
        ~ProjectTask.employee_id.in_(employee_ids)
    ).all() if collaborator_task_ids else []

    personal_task_items = []
    for task in {t.id: t for t in (tasks_direct + tasks_collab)}.values():
        item = _build_task_summary_item(task, company_map, today)
        if item:
            personal_task_items.append(item)

    collaborator_instance_ids = {
        c.process_instance_id
        for c in ProcessInstanceCollaborator.query.filter(
            ProcessInstanceCollaborator.employee_id.in_(employee_ids),
            ProcessInstanceCollaborator.is_deleted == False
        ).all()
        if c.process_instance_id
    } if employee_ids else set()

    process_direct = ProcessInstance.query.filter(
        db.or_(
            ProcessInstance.responsible_id.in_(employee_ids),
            ProcessInstance.executor_id.in_(employee_ids),
            ProcessInstance.owner_employee_id.in_(employee_ids)
        ),
        ProcessInstance.status != 'completed'
    ).all() if employee_ids else []

    process_collab = ProcessInstance.query.filter(
        ProcessInstance.id.in_(collaborator_instance_ids),
        ProcessInstance.status != 'completed'
    ).all() if collaborator_instance_ids else []

    personal_process_instances = list({p.id: p for p in (process_direct + process_collab)}.values())
    owner_ids = {
        getattr(p, "owner_employee_id", None) for p in personal_process_instances
    } | {
        getattr(p, "responsible_id", None) for p in personal_process_instances
    } | {
        getattr(p, "executor_id", None) for p in personal_process_instances
    }
    owner_ids = {oid for oid in owner_ids if oid}
    owner_lookup = {e.id: e.name for e in Employee.query.filter(Employee.id.in_(owner_ids)).all()} if owner_ids else {}

    personal_process_items = []
    for instance in personal_process_instances:
        item = _build_process_summary_item(instance, company_map, owner_lookup, today)
        if item:
            personal_process_items.append(item)

    meetings_q = Meeting.query.filter(
        Meeting.company_id.in_(company_ids),
        func.lower(func.coalesce(Meeting.status, "")) != "completed",
        Meeting.scheduled_date.isnot(None),
    ) if company_ids else []
    potential_meetings = meetings_q.all() if company_ids else []
    personal_meeting_items = []
    for meeting in potential_meetings:
        if _is_meeting_for_user(meeting, emails=emails, names=names):
            item = _build_meeting_summary_item(meeting, company_map, today)
            if item:
                personal_meeting_items.append(item)

    personal_items = _sort_summary_items(personal_task_items + personal_process_items)
    personal_overdue = [item for item in personal_items if item["due_date"] < today]
    personal_period = [item for item in personal_items if start_date <= item["due_date"] <= end_date]
    meeting_today = [item for item in personal_meeting_items if item["due_date"] == today]
    meeting_next_7_days = [item for item in personal_meeting_items if today < item["due_date"] <= today + timedelta(days=7)]

    pending_actions = []
    if role == "admin" and company_ids:
        pending_actions = AgentAction.query.filter(
            AgentAction.company_id.in_(company_ids),
            AgentAction.status.in_(["pending", "awaiting_approval"])
        ).order_by(AgentAction.created_at.asc()).all()

    team_overdue_extra = []
    team_period_extra = []
    if role == "client" and company_ids:
        team_tasks = ProjectTask.query.join(Project, Project.id == ProjectTask.project_id).filter(
            Project.company_id.in_(company_ids),
            ProjectTask.stage != 'completed'
        ).all()
        team_processes = ProcessInstance.query.filter(
            ProcessInstance.company_id.in_(company_ids),
            ProcessInstance.status != 'completed'
        ).all()

        extra_owner_ids = {
            getattr(p, "owner_employee_id", None) for p in team_processes
        } | {
            getattr(p, "responsible_id", None) for p in team_processes
        } | {
            getattr(p, "executor_id", None) for p in team_processes
        }
        extra_owner_ids = {oid for oid in extra_owner_ids if oid}
        extra_owner_lookup = owner_lookup.copy()
        if extra_owner_ids:
            extra_owner_lookup.update({
                e.id: e.name for e in Employee.query.filter(Employee.id.in_(extra_owner_ids)).all()
            })

        personal_keys = {(item["kind"], item["id"]) for item in personal_items}
        all_team_items = []

        for task in team_tasks:
            item = _build_task_summary_item(task, company_map, today)
            if item and (item["kind"], item["id"]) not in personal_keys:
                all_team_items.append(item)

        for instance in team_processes:
            item = _build_process_summary_item(instance, company_map, extra_owner_lookup, today)
            if item and (item["kind"], item["id"]) not in personal_keys:
                all_team_items.append(item)

        all_team_items = _sort_summary_items(all_team_items)
        team_overdue_extra = [item for item in all_team_items if item["due_date"] < today]
        team_period_extra = [item for item in all_team_items if start_date <= item["due_date"] <= end_date]

    return {
        "role": role,
        "today": today,
        "range_label": range_label,
        "date_range": date_range,
        "company_ids": company_ids,
        "personal_items": personal_items,
        "personal_overdue": personal_overdue,
        "personal_period": personal_period,
        "pending_actions": pending_actions,
        "next_7_days": [item for item in personal_items if today < item["due_date"] <= today + timedelta(days=7)],
        "meeting_today": meeting_today,
        "meeting_next_7_days": meeting_next_7_days,
        "team_overdue_extra": team_overdue_extra,
        "team_period_extra": team_period_extra,
        "team_next_7_days_extra": [item for item in all_team_items if today < item["due_date"] <= today + timedelta(days=7)] if role == "client" and company_ids else [],
    }


def _build_short_summary_message(user, summary: dict, channel: str) -> str:
    normalized_channel = str(channel or "telegram").strip().lower()
    role = summary["role"]
    today = summary["today"]
    personal_overdue = summary["personal_overdue"]
    personal_period = summary["personal_period"]
    next_7_days = summary.get("next_7_days") or []
    meeting_today = summary.get("meeting_today") or []
    meeting_next_7_days = summary.get("meeting_next_7_days") or []
    pending_actions = summary["pending_actions"]
    team_overdue_extra = summary["team_overdue_extra"]
    team_period_extra = summary["team_period_extra"]
    team_next_7_days_extra = summary.get("team_next_7_days_extra") or []
    target_window = _describe_summary_target_window(summary.get("date_range") or "today")

    lines = [f"Bom dia, {user.name}! Resumo de hoje ({today.strftime('%d/%m/%Y')}):"]

    if personal_overdue or personal_period or next_7_days or meeting_today or meeting_next_7_days:
        lines.append(f"• {len(personal_overdue)} atrasada(s)")
        lines.append(f"• {len(personal_period)} {target_window}")
        lines.append(f"• {len(next_7_days)} para os próximos 7 dias")
        lines.append(f"• {len(meeting_today)} reunião(ões) hoje e {len(meeting_next_7_days)} nos próximos 7 dias")
        lines.append("")
        lines.append("Principais itens:")
        spotlight = _sort_summary_items(personal_overdue + personal_period + next_7_days + meeting_today + meeting_next_7_days)[:3]
        for idx, item in enumerate(spotlight, start=1):
            lines.append(
                f"{idx}. {item['code']} — {item['title']} ({item['group_type']}: {item['group_label']}) — {item['due_label']}."
            )
    else:
        lines.append("• 0 atrasada(s)")
        lines.append(f"• 0 {target_window}")
        lines.append("• 0 para os próximos 7 dias")
        lines.append("• 0 reunião(ões) hoje e 0 nos próximos 7 dias")

    if role == "client":
        lines.append("")
        lines.append("Além disso, sua equipe tem:")
        lines.append(f"• {len(team_overdue_extra)} atrasada(s)")
        lines.append(f"• {len(team_period_extra)} {target_window}")
        lines.append(f"• {len(team_next_7_days_extra)} para os próximos 7 dias")
        if team_overdue_extra or team_period_extra or team_next_7_days_extra:
            lines.append("")
            lines.append("Quer que eu mostre agora? Responda SIM.")

    if role == "admin" and pending_actions:
        lines.append("")
        lines.append("Sistema:")
        lines.append(f"• {len(pending_actions)} ação(ões) do squad/correção aguardando decisão")
        for idx, action in enumerate(pending_actions[:3], start=1):
            agent = (action.requesting_agent or "agente").upper()
            lines.append(f"{idx}. {agent} — {action.title}")
        if len(pending_actions) > 3:
            lines.append(f"...e mais {len(pending_actions) - 3}.")

    lines.append("")
    if normalized_channel == "email":
        lines.append("Se quiser, responda este e-mail e eu detalho a lista.")
    else:
        lines.append("Se quiser, eu posso detalhar a lista no chat.")

    inspiration = _get_daily_inspiration(today)
    if inspiration:
        lines.append("")
        lines.append(inspiration)

    return "\n".join(lines)


def _build_team_details_message(user, summary: dict, channel: str) -> str:
    items = _sort_summary_items(summary["team_overdue_extra"] + summary["team_period_extra"])
    if not items:
        return f"{user.name}, não encontrei outras atividades da equipe além das que já enviei no resumo."

    grouped = defaultdict(lambda: defaultdict(list))
    for item in items:
        responsible = item.get("responsible") or "Sem responsável"
        grouped[responsible][item["group_label"]].append(item)

    lines = ["Segue o detalhamento da equipe por responsável e projeto/processo:"]
    for responsible in sorted(grouped.keys()):
        lines.append(f"• {responsible}")
        for group_label in sorted(grouped[responsible].keys()):
            lines.append(f"  - {group_label}")
            for item in grouped[responsible][group_label][:8]:
                lines.append(f"    • {item['code']} — {item['title']} ({_format_date_br(item['due_date'])})")

    message = "\n".join(lines)
    if channel == "telegram":
        return _truncate_telegram_message(message)
    return message


def get_user_summary_report(user, date_range='today', channel='telegram'):
    """
    Gera o relatório de resumo para um usuário específico.
    """
    normalized_channel = str(channel or "telegram").strip().lower()
    summary = _build_summary_context(user, date_range=date_range)
    if not summary:
        return None

    message = _build_short_summary_message(user, summary, normalized_channel)
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
    theme = get_summary_email_theme()
    safe_user = html.escape(str(user_name or "Colaborador"))
    safe_range = html.escape(str(range_label or "de hoje"))
    safe_generated_at = html.escape(str(generated_at or ""))
    body_html = _render_summary_body_html(body_text or "")

    return f"""
<!doctype html>
<html lang="pt-BR">
  <body style="margin:0;padding:0;background:{theme['page_bg']};font-family:Segoe UI,Arial,sans-serif;color:{theme['text_primary']};">
    <div style="max-width:920px;margin:24px auto;padding:0 14px;">
      <div style="background:{theme['header_gradient']};color:#fff;border-radius:16px;padding:24px 28px;box-shadow:0 8px 22px rgba(15,23,42,.22);">
        <div style="font-size:11px;opacity:.95;letter-spacing:.8px;text-transform:uppercase;font-weight:700;">Sapiens • Versus Gestão Corporativa</div>
        <h1 style="margin:10px 0 6px;font-size:25px;line-height:1.25;font-weight:800;">Resumo de atividades {safe_range}</h1>
        <div style="font-size:14px;opacity:.98;line-height:1.5;">
          Colaborador: <strong>{safe_user}</strong><br>
          Data base: <strong>{safe_generated_at}</strong>
        </div>
      </div>

      <div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-radius:16px;padding:22px 24px;margin-top:14px;line-height:1.65;">
        {body_html}
      </div>

      <div style="background:{theme['card_bg']};border:1px solid {theme['card_border']};border-radius:16px;padding:18px 24px;margin-top:14px;">
        <div style="font-size:16px;font-weight:800;color:{theme['text_primary']};">Sapiens Versus</div>
        <div style="font-size:14px;color:{theme['signature_accent']};font-weight:700;margin-top:2px;">Versus Gestão Corporativa</div>
        <div style="font-size:13px;color:{theme['text_secondary']};margin-top:8px;">
          E-mail:
          <a href="mailto:sapiens@gestaoversus.com.br" style="color:{theme['signature_accent']};text-decoration:none;">sapiens@gestaoversus.com.br</a>
        </div>
        <div style="font-size:13px;color:{theme['text_secondary']};margin-top:4px;">Telefone: 71 9 8238-5225</div>
        <div style="margin-top:14px;">
          <img src="cid:versus_signature_logo" alt="Versus Gestão Corporativa" style="max-width:280px;width:100%;height:auto;display:block;border:0;">
        </div>
      </div>

      <div style="text-align:center;color:{theme['text_muted']};font-size:12px;margin:14px 0 6px;">
        Mensagem automática enviada pelo Sapiens.
      </div>
    </div>
  </body>
</html>
"""


def _render_summary_body_html(body_text: str) -> str:
    theme = get_summary_email_theme()
    lines = str(body_text or "").splitlines()
    parts = []
    current_section = None
    expect_company_name = False

    def _norm(text: str) -> str:
        normalized = unicodedata.normalize("NFD", str(text or "").lower().strip())
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    section_styles = get_summary_email_section_styles()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            parts.append("<div style='height:8px;'></div>")
            continue

        stripped = line.strip()
        lowered = stripped.lower()

        if lowered.startswith("olá,") or lowered.startswith("ola,"):
            parts.append(
                f"<div style='font-size:17px;font-weight:800;color:{theme['text_primary']};margin:0 0 8px;'>{html.escape(stripped)}</div>"
            )
            continue

        if lowered.startswith("sou o sapiens"):
            parts.append(
                f"<div style='font-size:14px;color:{theme['text_secondary']};margin:0 0 10px;'>{html.escape(stripped)}</div>"
            )
            continue

        if "aprovações pendentes" in lowered or "aprovacoes pendentes" in lowered:
            parts.append(
                f"<div style='margin:10px 0 8px;padding:8px 12px;border-left:4px solid {theme['warning_border']};background:{theme['warning_bg']};color:{theme['warning_text']};font-size:13px;font-weight:800;border-radius:8px;'>{html.escape(stripped)}</div>"
            )
            continue

        if lowered.startswith("resumo das atividades"):
            parts.append(
                f"<div style='margin:10px 0 8px;padding:8px 12px;border-left:4px solid {theme['summary_chip_border']};background:{theme['summary_chip_bg']};color:{theme['summary_chip_text']};font-size:13px;font-weight:800;border-radius:8px;'>{html.escape(stripped)}</div>"
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
                f"<div style='margin:12px 0 8px;padding:10px 14px;border:1px solid {theme['company_box_border']};"
                f"border-left:5px solid {theme['company_box_border_accent']};border-radius:12px;background:{theme['company_box_bg']};'>"
                f"<div style='font-size:11px;font-weight:800;color:{theme['company_box_label']};letter-spacing:.6px;"
                "text-transform:uppercase;margin-bottom:3px;'>Empresa</div>"
                f"<div style='font-size:16px;font-weight:800;color:{theme['text_primary']};'>{company_name}</div>"
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
            section_color = section_styles[current_section]["color"] if current_section else theme["text_secondary"]
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
                        f"<div style='margin:4px 0 4px 64px;padding:7px 10px;background:{theme['item_bg_soft']};"
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
                f"<div style='margin:4px 0 4px 8px;font-size:14px;color:{theme['text_primary']};'>• {content}</div>"
            )
            continue

        if line.startswith("    - "):
            content = html.escape(line[6:].strip())
            section_color = section_styles[current_section]["color"] if current_section else theme["text_secondary"]
            parts.append(
                f"<div style='margin:4px 0 4px 64px;padding:7px 10px;background:{theme['item_bg_soft']};"
                f"border-left:3px solid {section_color};border-radius:8px;font-size:13px;color:#1e293b;'>"
                f"{content}</div>"
            )
            continue

        if re.match(r"^\d+\.\s", stripped):
            parts.append(
                f"<div style='margin:4px 0 4px 8px;font-size:14px;color:{theme['text_primary']};font-weight:600;'>{html.escape(stripped)}</div>"
            )
            continue

        parts.append(
            f"<div style='margin:4px 0;font-size:14px;color:{theme['text_primary']};'>{html.escape(stripped)}</div>"
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


def _find_recent_summary_prompt_message(
    user_id: int,
    company_id: int,
    channel: str,
    metadata_key: str,
    lookback_minutes: int = 1440,
):
    from models.agent_message import AgentMessage

    cutoff = datetime.utcnow() - timedelta(minutes=lookback_minutes)
    candidates = AgentMessage.query.filter(
        AgentMessage.user_id == user_id,
        AgentMessage.company_id == company_id,
        AgentMessage.channel == channel,
        AgentMessage.direction == "outbound",
        AgentMessage.created_at >= cutoff,
    ).order_by(AgentMessage.created_at.desc()).limit(20).all()

    for candidate in candidates:
        metadata = candidate.metadata_json or {}
        if metadata.get(metadata_key):
            return candidate
    return None


def _handle_summary_email_confirmation(user, company_id: int, incoming_text: str, channel: str):
    if not _is_affirmative_email_confirmation(incoming_text):
        return False, None

    offer_message = _find_recent_summary_prompt_message(
        user_id=user.id,
        company_id=company_id,
        channel=channel,
        metadata_key="email_offer_available",
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


def _handle_summary_team_details_confirmation(user, company_id: int, incoming_text: str, channel: str):
    if not _is_affirmative_email_confirmation(incoming_text):
        return False, None

    offer_message = _find_recent_summary_prompt_message(
        user_id=user.id,
        company_id=company_id,
        channel=channel,
        metadata_key="summary_team_offer_available",
    )
    if not offer_message:
        return False, None

    metadata = offer_message.metadata_json or {}
    if str(metadata.get("summary_user_role") or "") != "client":
        return False, None

    date_range = str(metadata.get("summary_date_range") or "").strip() or _infer_date_range_from_summary_text(offer_message.content)
    summary = _build_summary_context(user, date_range=date_range)
    if not summary:
        return True, "Não consegui montar o detalhamento da equipe agora."

    return True, _build_team_details_message(user, summary, channel)


def try_handle_summary_followup(user, company_id: int, incoming_text: str, channel: str = "telegram"):
    if not user or not company_id:
        return False, None

    handled, response = _handle_summary_team_details_confirmation(user, company_id, incoming_text, channel)
    if handled:
        return handled, response

    return _handle_summary_email_confirmation(user, company_id, incoming_text, channel)


def try_handle_summary_email_confirmation(user, company_id: int, incoming_text: str, channel: str = "telegram"):
    return _handle_summary_email_confirmation(user, company_id, incoming_text, channel)


def _log_summary_agent_message(user, company_id: int, channel: str, recipient: str, message: str, date_range: str, preferred_channels: list[str] | None = None, delivery_sequence: list[str] | None = None, fallback_used: bool = False, winner_channel: str | None = None):
    try:
        from models.agent_message import AgentMessage

        summary = _build_summary_context(user, date_range=date_range) or {}
        metadata = {
            "contact": "sapiens",
            "summary_date_range": date_range,
            "summary_user_role": summary.get("role"),
            "summary_team_offer_available": bool(summary.get("role") == "client" and (summary.get("team_overdue_extra") or summary.get("team_period_extra"))),
            "email_offer_available": EMAIL_FALLBACK_FRAGMENT in (message or ""),
            "recipient": str(recipient),
            "preferred_channels": list(preferred_channels or []),
            "delivery_sequence": list(delivery_sequence or []),
            "fallback_used": bool(fallback_used),
            "winner_channel": winner_channel or channel,
        }
        if channel == 'telegram':
            metadata.update({
                "thread_id": f"tg_{recipient}",
                "telegram_id": str(recipient),
            })
        elif channel == 'whatsapp':
            metadata.update({
                "thread_id": f"wa_{recipient}",
                "whatsapp": str(recipient),
            })
        elif channel == 'email':
            metadata.update({
                "thread_id": f"email_{user.id}",
                "email": str(recipient),
            })

        db.session.add(AgentMessage(
            company_id=company_id,
            user_id=user.id,
            agent_type='work_agent_squad',
            agent_name='sapiens',
            direction='outbound',
            channel=channel,
            content=message,
            metadata_json=metadata,
        ))
        db.session.commit()
    except Exception as log_err:
        db.session.rollback()
        logger.warning("Falha ao registrar AgentMessage do resumo proativo: %s", log_err)


def send_morning_summaries(app):
    """
    Scans active users and sends the morning summary using preferred channels
    with automatic fallback to other available channels.
    """
    with app.app_context():
        logger.info("🌤️ Iniciando envio de resumos matinais proativos...")
        users = User.query.filter(User.is_active == True).all()
        for user in users:
            try:
                preferred_channels = _resolve_summary_delivery_channels(user)
                attempt_order = _build_summary_attempt_order(user)
                if not attempt_order:
                    logger.warning("Usuário %s sem canais disponíveis para resumo matinal.", user.id)
                    continue

                try:
                    from src.intelligence.identity import get_best_company_id
                    summary_company_id = get_best_company_id(user)
                except Exception:
                    summary_company_id = None

                delivered_channels = []
                fallback_channels = []
                attempted_channels = []
                winning_channel = None

                for index, channel in enumerate(attempt_order):
                    attempted_channels.append(channel)
                    recipient = _format_summary_recipient(user, channel)
                    if not recipient:
                        logger.warning(
                            "Usuário %s sem destino configurado para o canal %s; resumo ignorado.",
                            user.id,
                            channel,
                        )
                        continue

                    result = _send_summary_via_channel(user, date_range='today', channel=channel)
                    if not result.get('success'):
                        logger.warning(
                            "Falha ao enviar resumo matinal para user=%s canal=%s erro=%s",
                            user.id,
                            channel,
                            result.get('error'),
                        )
                        continue

                    delivered_channels.append(channel)
                    winning_channel = winning_channel or channel
                    if channel not in preferred_channels:
                        fallback_channels.append(channel)

                    message = result.get('message') or ''
                    logger.info(
                        "Resumo matinal enviado para %s via %s (%s chars)",
                        user.name,
                        channel,
                        len(message),
                    )

                    if summary_company_id:
                        _log_summary_agent_message(
                            user=user,
                            company_id=summary_company_id,
                            channel=channel,
                            recipient=recipient,
                            message=message,
                            date_range='today',
                            preferred_channels=preferred_channels,
                            delivery_sequence=attempted_channels,
                            fallback_used=channel not in preferred_channels,
                            winner_channel=winning_channel or channel,
                        )

                    should_continue = channel in preferred_channels
                    if not should_continue and index >= len(preferred_channels):
                        break

                if not delivered_channels:
                    logger.error(
                        "Resumo matinal não entregue ao usuário %s. Preferidos=%s Disponíveis=%s",
                        user.id,
                        preferred_channels,
                        attempt_order,
                    )
                elif fallback_channels:
                    logger.info(
                        "Fallback automático aplicado para user=%s. Preferidos=%s Tentativas=%s Entregues=%s Fallback=%s Vencedor=%s",
                        user.id,
                        preferred_channels,
                        attempted_channels,
                        delivered_channels,
                        fallback_channels,
                        winning_channel,
                    )
                else:
                    logger.info(
                        "Resumo matinal entregue sem fallback para user=%s. Preferidos=%s Tentativas=%s Vencedor=%s",
                        user.id,
                        preferred_channels,
                        attempted_channels,
                        winning_channel,
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
