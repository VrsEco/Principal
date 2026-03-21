from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func

from models import Employee, Portfolio, Project, ProjectTask, User
from services.notification_hub import notification_hub
from services.proactive_service import _build_summary_attempt_order


def _format_date_br(value) -> str:
    if not value:
        return 'Não definido'
    if hasattr(value, 'strftime'):
        return value.strftime('%d/%m/%Y')
    try:
        return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y')
    except Exception:
        return str(value)


def _normalize_text(value: Any, fallback: str = 'Não informado') -> str:
    normalized = str(value or '').strip()
    return normalized or fallback


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def _resolve_user_from_employee(employee: Employee | None) -> User | None:
    if not employee or not getattr(employee, 'user_id', None):
        return None
    user = User.query.get(employee.user_id)
    if not user or not getattr(user, 'is_active', False):
        return None
    return user


def get_project_owner_user(project: Project) -> User | None:
    owner_name = _normalize_text(getattr(project, 'owner', None), fallback='')
    if not owner_name:
        return None
    employee = Employee.query.filter(
        Employee.company_id == project.company_id,
        Employee.status == 'active',
        func.lower(Employee.name) == owner_name.lower(),
    ).first()
    return _resolve_user_from_employee(employee)


def get_task_responsible_user(task: ProjectTask) -> User | None:
    return _resolve_user_from_employee(getattr(task, 'employee', None))


def get_portfolio_responsible_user(portfolio: Portfolio) -> User | None:
    return _resolve_user_from_employee(getattr(portfolio, 'responsible', None))


def _channel_enabled(user: User | None, channel: str) -> bool:
    if not user:
        return False
    if channel == 'email':
        return bool(getattr(user, 'email', None))
    if channel == 'whatsapp':
        return bool(getattr(user, 'whatsapp', None))
    if channel == 'telegram':
        return bool(getattr(user, 'telegram', None))
    return False




def build_summary_hint(user: User | None) -> str | None:
    if not user:
        return 'Responsável sem usuário ativo vinculado para envio digital.'
    available = []
    if _channel_enabled(user, 'email'):
        available.append('E-mail')
    if _channel_enabled(user, 'whatsapp'):
        available.append('WhatsApp')
    if available:
        return None
    return 'Responsável sem E-mail ou WhatsApp configurados no perfil. PDF permanece disponível.'

def build_summary_options(user: User | None, pdf_url: str, send_url: str) -> list[dict[str, str]]:
    options = [{'channel': 'pdf', 'label': 'PDF', 'kind': 'download', 'url': pdf_url}]
    if _channel_enabled(user, 'email'):
        options.append({'channel': 'email', 'label': 'E-mail', 'kind': 'send', 'url': send_url})
    if _channel_enabled(user, 'whatsapp'):
        options.append({'channel': 'whatsapp', 'label': 'WhatsApp', 'kind': 'send', 'url': send_url})
    return options


def _send_payload_to_user(user: User, payload: dict[str, str | None], preferred_channel: str | None = None) -> dict[str, Any]:
    attempt_order = [preferred_channel] if preferred_channel else _build_summary_attempt_order(user)
    if not attempt_order:
        return {'success': False, 'error': 'Usuário sem canais configurados para envio'}
    for channel in attempt_order:
        normalized = (channel or '').strip().lower()
        if normalized == 'email':
            result = notification_hub.send_email(user.email, payload['subject'], payload['body'], html_body=payload.get('html_body'))
        else:
            result = notification_hub.send_to_user(user, normalized, payload['body'], subject=payload['subject'], html_body=payload.get('html_body'), parse_mode='HTML')
        if result.get('success'):
            result['delivery_channel'] = normalized
            result['subject'] = payload['subject']
            return result
    return {'success': False, 'error': 'Falha ao enviar resumo em todos os canais configurados', 'attempted_channels': attempt_order}


def _build_task_summary_payload(task: ProjectTask) -> dict[str, str | None]:
    project = task.project
    where_label = f'{project.code} - {project.name}' if project else 'Projeto não identificado'
    responsible_name = _normalize_text(getattr(task, 'employee_name', None) or getattr(task, 'who', None), 'Sem responsável definido')
    task_code = getattr(task, 'code', None) or f'J.{task.id}'
    score_weight = _to_float(getattr(task, 'score_weight', None), 1.0)
    return {
        'subject': f'Resumo da Atividade - {task_code}',
        'body': (
            f'Olá, {responsible_name}!\n\n'
            'Segue o resumo da atividade sob sua responsabilidade:\n\n'
            '5W1H da atividade:\n'
            f'- Código: {task_code}\n'
            f'- O que: {_normalize_text(task.what)}\n'
            f'- Quem: {responsible_name}\n'
            f'- Quando: {_format_date_br(task.due_date)}\n'
            f'- Onde: {where_label}\n'
            f'- Como: {_normalize_text(getattr(task, "how", None))}\n'
            f'- Status: {_normalize_text(task.status)}\n'
            f'- Etapa: {_normalize_text(task.stage)}\n'
            f'- Horas previstas: {_to_float(task.estimated_hours):.1f}h\n'
            f'- Horas realizadas: {_to_float(task.worked_hours):.1f}h\n'
            f'- Peso: {score_weight:.2f}\n'
        ),
        'html_body': None,
    }


def _build_project_summary_payload(project: Project) -> dict[str, str | None]:
    stats = getattr(project, 'task_stats', None) or {}
    tasks = []
    task_query = getattr(project, 'tasks', None)
    if task_query is not None and hasattr(task_query, 'order_by'):
        try:
            tasks = task_query.order_by(ProjectTask.due_date.asc(), ProjectTask.id.asc()).all()
        except Exception:
            tasks = task_query.all() if hasattr(task_query, 'all') else []

    prioritized_lines = []
    for index, task in enumerate(tasks[:5], start=1):
        prioritized_lines.append(
            f"{index}. {getattr(task, 'code', None) or f'J.{task.id}'} | "
            f"{_normalize_text(getattr(task, 'what', None))} | "
            f"Responsável: {_normalize_text(getattr(task, 'employee_name', None) or getattr(task, 'who', None), 'Não definido')} | "
            f"Prazo: {_format_date_br(getattr(task, 'due_date', None))} | "
            f"Status: {_normalize_text(getattr(task, 'status', None))}"
        )

    prioritized_block = '\n'.join(prioritized_lines) if prioritized_lines else '- Nenhuma atividade priorizada encontrada.\n'
    return {
        'subject': f'Resumo do Projeto - {project.code} - {project.name}',
        'body': (
            f'Olá, {_normalize_text(project.owner, "Responsável do projeto")}!\n\n'
            'Segue o resumo consolidado do projeto:\n\n'
            'Panorama do projeto:\n'
            f'- Projeto: {project.code} - {project.name}\n'
            f'- Responsável: {_normalize_text(project.owner, "Não definido")}\n'
            f'- Status: {_normalize_text(project.status)}\n'
            f'- Prazo: {_format_date_br(project.deadline)}\n'
            f'- Progresso: {int(stats.get("progress", 0))}%\n'
            f'- Total: {int(stats.get("total", 0))}\n'
            f'- Em aberto: {int(stats.get("open", 0))}\n'
            f'- Concluídas: {int(stats.get("completed", 0))}\n'
            f'- Atrasadas: {int(stats.get("delayed", 0))}\n'
            '\n'
            'Atividades priorizadas:\n'
            f'{prioritized_block}'
        ),
        'html_body': None,
    }


def _build_portfolio_summary_payload(portfolio: Portfolio) -> dict[str, str | None]:
    projects = Project.query.filter_by(company_id=portfolio.company_id, portfolio_id=portfolio.id).order_by(Project.deadline.asc().nullslast(), Project.id.asc()).all()
    progress_values = [int(project.task_stats.get('progress', 0)) for project in projects]
    avg_progress = round(sum(progress_values) / len(progress_values)) if progress_values else 0
    return {
        'subject': f'Resumo do Portfólio - {portfolio.code} - {portfolio.name}',
        'body': (
            f'Olá, {_normalize_text(getattr(portfolio.responsible, "name", None), "Responsável do portfólio")}!\n\n'
            'Segue o resumo consolidado do portfólio:\n\n'
            f'- Portfólio: {portfolio.code} - {portfolio.name}\n'
            f'- Responsável: {_normalize_text(getattr(portfolio.responsible, "name", None))}\n'
            f'- Total de projetos: {len(projects)}\n'
            f'- Progresso médio: {avg_progress}%\n'
        ),
        'html_body': None,
    }


def send_task_summary_to_responsible(task: ProjectTask, preferred_channel: str | None = None) -> dict[str, Any]:
    user = get_task_responsible_user(task)
    if not user:
        return {'success': False, 'error': 'Responsável da atividade sem usuário ativo vinculado'}
    result = _send_payload_to_user(user, _build_task_summary_payload(task), preferred_channel=preferred_channel)
    result['target_user_id'] = user.id
    return result


def send_project_summary_to_owner(project: Project, preferred_channel: str | None = None) -> dict[str, Any]:
    user = get_project_owner_user(project)
    if not user:
        return {'success': False, 'error': 'Responsável do projeto sem usuário ativo vinculado'}
    result = _send_payload_to_user(user, _build_project_summary_payload(project), preferred_channel=preferred_channel)
    result['target_user_id'] = user.id
    return result


def send_portfolio_summary_to_responsible(portfolio: Portfolio, preferred_channel: str | None = None) -> dict[str, Any]:
    user = get_portfolio_responsible_user(portfolio)
    if not user:
        return {'success': False, 'error': 'Responsável do portfólio sem usuário ativo vinculado'}
    result = _send_payload_to_user(user, _build_portfolio_summary_payload(portfolio), preferred_channel=preferred_channel)
    result['target_user_id'] = user.id
    return result
