from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func

from models import Employee, Project, ProjectTask, User
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


def _resolve_user_from_employee(employee: Employee | None) -> User | None:
    if not employee or not getattr(employee, 'user_id', None):
        return None
    user = User.query.get(employee.user_id)
    if not user or not getattr(user, 'is_active', False):
        return None
    return user


def _resolve_project_owner_user(project: Project) -> User | None:
    owner_name = _normalize_text(getattr(project, 'owner', None), fallback='')
    if not owner_name:
        return None

    employee = Employee.query.filter(
        Employee.company_id == project.company_id,
        Employee.status == 'active',
        func.lower(Employee.name) == owner_name.lower(),
    ).first()
    return _resolve_user_from_employee(employee)


def _build_task_summary_payload(task: ProjectTask) -> dict[str, str | None]:
    project = task.project
    where_label = f'{project.code} - {project.name}' if project else 'Projeto não identificado'
    responsible_name = _normalize_text(
        getattr(task, 'employee_name', None) or getattr(task, 'who', None),
        'Sem responsável definido',
    )
    how_label = _normalize_text(getattr(task, 'how', None))
    subject = f'Resumo da Atividade - {task.code or f"J.{task.id}"}'
    body = (
        f'Olá, {responsible_name}!\n\n'
        'Segue o resumo objetivo da atividade sob sua responsabilidade:\n\n'
        '5W1H da atividade:\n'
        f'- O que: {_normalize_text(task.what)}\n'
        f'- Quem: {responsible_name}\n'
        f'- Quando: {_format_date_br(task.due_date)}\n'
        f'- Onde: {where_label}\n'
        f'- Como: {how_label}\n\n'
        'Contexto complementar:\n'
        f'- Status: {_normalize_text(task.status)}\n'
        f'- Etapa: {_normalize_text(task.stage)}\n'
        f'- Prioridade: {_normalize_text(task.priority, "Normal")}\n'
        f'- Horas previstas: {float(task.estimated_hours or 0):.1f}h\n'
        f'- Horas realizadas: {float(task.worked_hours or 0):.1f}h\n\n'
        'Se quiser, posso detalhar também dependências, diário de bordo e próximos passos.'
    )
    return {'subject': subject, 'body': body, 'html_body': None}


def _build_project_summary_payload(project: Project) -> dict[str, str | None]:
    tasks = list(project.tasks.order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc()).all())
    stats = project.task_stats
    open_tasks = [task for task in tasks if (task.stage or '').lower() != 'completed']
    top_tasks = open_tasks[:10]

    task_lines = []
    for index, task in enumerate(top_tasks, start=1):
        task_lines.append(
            f'{index}. {task.code or f"J.{project.id}.{task.id}"} | {_normalize_text(task.what)} | '
            f'Responsável: {_normalize_text(getattr(task, "employee_name", None) or getattr(task, "who", None), "Sem responsável definido")} | '
            f'Prazo: {_format_date_br(task.due_date)} | Status: {_normalize_text(task.stage or task.status)}'
        )

    if not task_lines:
        task_lines.append('1. Nenhuma atividade aberta no momento.')

    subject = f'Resumo do Projeto - {project.code} - {project.name}'
    body = (
        f'Olá, {_normalize_text(project.owner, "Responsável do projeto")}!\n\n'
        'Segue o resumo executivo do projeto, consolidado no formato do resumo diário:\n\n'
        'Panorama do projeto:\n'
        f'- Projeto: {project.code} - {project.name}\n'
        f'- Responsável: {_normalize_text(project.owner, "Não definido")}\n'
        f'- Status: {_normalize_text(project.status)}\n'
        f'- Prazo: {_format_date_br(project.deadline)}\n'
        f'- Progresso: {int(stats.get("progress", 0))}%\n\n'
        'Indicadores de atividades:\n'
        f'- Total: {int(stats.get("total", 0))}\n'
        f'- Em aberto: {int(stats.get("open", 0))}\n'
        f'- Concluídas: {int(stats.get("completed", 0))}\n'
        f'- Atrasadas: {int(stats.get("delayed", 0))}\n\n'
        'Atividades priorizadas:\n'
        + '\n'.join(task_lines)
        + '\n\n'
        + 'Se quiser, posso gerar também uma leitura por etapa do Kanban ou por responsável.'
    )
    return {'subject': subject, 'body': body, 'html_body': None}


def _send_payload_to_user(user: User, payload: dict[str, str | None]) -> dict[str, Any]:
    attempt_order = _build_summary_attempt_order(user)
    if not attempt_order:
        return {'success': False, 'error': 'Usuário sem canais configurados para envio'}

    for channel in attempt_order:
        if channel == 'email':
            result = notification_hub.send_email(
                user.email,
                payload['subject'],
                payload['body'],
                html_body=payload.get('html_body'),
            )
        else:
            result = notification_hub.send_to_user(
                user,
                channel,
                payload['body'],
                subject=payload['subject'],
                html_body=payload.get('html_body'),
                parse_mode='HTML',
            )
        if result.get('success'):
            result['delivery_channel'] = channel
            result['subject'] = payload['subject']
            return result

    return {
        'success': False,
        'error': 'Falha ao enviar resumo em todos os canais configurados',
        'attempted_channels': attempt_order,
    }


def send_task_summary_to_responsible(task: ProjectTask) -> dict[str, Any]:
    user = _resolve_user_from_employee(getattr(task, 'employee', None))
    if not user:
        return {'success': False, 'error': 'Responsável da atividade sem usuário ativo vinculado'}
    payload = _build_task_summary_payload(task)
    result = _send_payload_to_user(user, payload)
    result['target_user_id'] = user.id
    return result


def send_project_summary_to_owner(project: Project) -> dict[str, Any]:
    user = _resolve_project_owner_user(project)
    if not user:
        return {'success': False, 'error': 'Responsável do projeto sem usuário ativo vinculado'}
    payload = _build_project_summary_payload(project)
    result = _send_payload_to_user(user, payload)
    result['target_user_id'] = user.id
    return result
