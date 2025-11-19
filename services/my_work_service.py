import logging

"""
Service para My Work - Lógica de negócio
Gerencia atividades pessoais, de equipe e da empresa
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Sequence
import json

from database.postgres_helper import connect as pg_connect


def get_employee_from_user(user_id: int) -> Optional[int]:
    """
    Mapeia user_id para employee_id
    
    EstratÃ©gia:
    1. Busca direta por user_id (relacionamento FK)
    2. Fallback: busca por email (para dados legados)
    
    Args:
        user_id: ID do usuÃ¡rio logado
    
    Returns:
        employee_id ou None
    """
    from models.user import User
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # 1. Buscar por user_id (relacionamento direto)
        cursor.execute("SELECT id FROM employees WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return row[0]
        
        # 2. Fallback: buscar por email (dados legados sem user_id preenchido)
        user = User.query.get(user_id)
        if user and user.email:
            cursor.execute("""
                SELECT id FROM employees 
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (user.email,))
            row = cursor.fetchone()
            
            if row:
                employee_id = row[0]
                
                # Auto-vincular para prÃ³ximas consultas
                try:
                    cursor.execute("""
                        UPDATE employees 
                        SET user_id = %s 
                        WHERE id = %s AND user_id IS NULL
                    """, (user_id, employee_id))
                    conn.commit()
                    logger.info(f"âœ… Auto-vinculado: User #{user_id} -> Employee #{employee_id}")
                except Exception as exc:
                    conn.rollback()
                
                conn.close()
                return employee_id
        
        conn.close()
        return None
        
    except Exception as e:
        logger.info(f"âŒ Erro ao mapear user_id para employee_id: {e}")
        conn.close()
        return None


def get_user_activities(employee_id: Optional[int], scope: str = 'me', filters: Dict = None) -> List[Dict]:
    """
    Retorna atividades conforme escopo
    
    Args:
        employee_id: ID do colaborador
        scope: 'me', 'team' ou 'company'
        filters: Filtros adicionais (filter, search, sort)
    
    Returns:
        Lista de atividades (projetos + processos)
    """
    if employee_id is None:
        return []
    
    filters = filters or {}
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        if scope == 'me':
            activities = _get_my_activities(cursor, employee_id, filters)
        elif scope == 'team':
            activities = _get_team_activities(cursor, employee_id, filters)
        elif scope == 'company':
            activities = _get_company_activities(cursor, employee_id, filters)
        else:
            activities = []
        
        conn.close()
        return activities
        
    except Exception as e:
        conn.close()
        raise e


def _get_my_activities(cursor, employee_id: int, filters: Dict) -> List[Dict]:
    """Busca atividades pessoais do colaborador"""
    
    project_rows = _fetch_projects_for_employee(cursor, employee_id)
    process_rows = _fetch_processes_for_employee(cursor, employee_id)
    
    activities = [_serialize_project_activity(row, employee_id) for row in project_rows]
    activities.extend(_serialize_process_activity(row, employee_id) for row in process_rows)
    
    activities = _apply_filters(activities, filters)
    activities = _apply_sort(activities, filters.get('sort', 'deadline'))
    
    return activities


def _get_team_activities(cursor, employee_id: int, filters: Dict) -> List[Dict]:
    """Busca atividades da equipe do colaborador"""
    member_ids = _fetch_team_member_ids(cursor, employee_id)
    if not member_ids:
        return []
    
    project_rows = _fetch_projects_for_members(cursor, member_ids)
    process_rows = _fetch_processes_for_members(cursor, member_ids)
    
    activities = [_serialize_project_activity(row, employee_id, member_ids=member_ids) for row in project_rows]
    activities.extend(_serialize_process_activity(row, employee_id, member_ids=member_ids) for row in process_rows)
    
    activities = _apply_filters(activities, filters)
    activities = _apply_sort(activities, filters.get('sort', 'deadline'))
    
    return activities


def _get_company_activities(cursor, employee_id: int, filters: Dict) -> List[Dict]:
    """Busca todas as atividades da empresa"""
    
    # Verificar permissÃ£o
    if not _can_view_company(cursor, employee_id):
        raise PermissionError("UsuÃ¡rio sem permissÃ£o para visualizar atividades da empresa")
    
    company_id = _fetch_employee_company_id(cursor, employee_id)
    if company_id is None:
        return []
    
    project_rows = _fetch_company_projects(cursor, company_id)
    process_rows = _fetch_company_processes(cursor, company_id)
    
    activities = [_serialize_project_activity(row, employee_id) for row in project_rows]
    activities.extend(_serialize_process_activity(row, employee_id) for row in process_rows)
    
    activities = _apply_filters(activities, filters)
    activities = _apply_sort(activities, filters.get('sort', 'deadline'))
    
    return activities


def get_user_stats(employee_id: Optional[int], scope: str = 'me') -> Dict:
    """
    Retorna estatÃ­sticas conforme escopo
    
    Returns:
        Dict com contadores
    """
    if employee_id is None:
        return {
            'pending': 0,
            'in_progress': 0,
            'overdue': 0,
            'completed': 0
        }
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        if scope == 'me':
            stats = _get_my_stats(cursor, employee_id)
        elif scope == 'team':
            stats = _get_team_stats(cursor, employee_id)
        elif scope == 'company':
            stats = _get_company_stats(cursor, employee_id)
        else:
            stats = {}
        
        conn.close()
        return stats
        
    except Exception as e:
        conn.close()
        raise e


def _get_my_stats(cursor, employee_id: int) -> Dict:
    """EstatÃ­sticas pessoais"""
    activities = _get_my_activities(cursor, employee_id, filters={})
    return _calculate_stats_from_activities(activities)


def _get_team_stats(cursor, employee_id: int) -> Dict:
    """EstatÃ­sticas da equipe"""
    activities = _get_team_activities(cursor, employee_id, filters={})
    return _calculate_stats_from_activities(activities)


def _get_company_stats(cursor, employee_id: int) -> Dict:
    """EstatÃ­sticas da empresa"""
    activities = _get_company_activities(cursor, employee_id, filters={})
    return _calculate_stats_from_activities(activities)


def count_activities_by_scope(employee_id: Optional[int]) -> Dict:
    """
    Conta atividades em cada escopo para os contadores das abas
    
    Returns:
        {'me': 17, 'team': 45, 'company': 180}
    """
    if employee_id is None:
        return {
            'me': 0,
            'team': 0,
            'company': 0
        }
    
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        count_me = _count_my_activities(cursor, employee_id)
        count_team = _count_team_activities(cursor, employee_id)
        count_company = _count_company_activities(cursor, employee_id)
        
        conn.close()
        
        return {
            'me': count_me,
            'team': count_team,
            'company': count_company
        }
        
    except Exception as e:
        conn.close()
        raise e


def _fetch_projects_for_employee(cursor, employee_id: int):
    """Busca projetos onde o colaborador Ã© responsÃ¡vel ou executor."""
    cursor.execute("""
        SELECT 
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            COALESCE(cp.status, 'planned') AS status,
            LOWER(COALESCE(cp.priority, 'normal')) AS priority,
            cp.responsible_id,
            cp.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.start_date,
            cp.end_date AS deadline_date,
            cp.estimated_hours,
            cp.worked_hours,
            cp.created_at,
            cp.updated_at,
            pl.name AS plan_name,
            co.name AS company_name
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies co ON co.id = cp.company_id
        WHERE (cp.responsible_id = %s OR cp.executor_id = %s)
    """, (employee_id, employee_id))
    
    return cursor.fetchall()


def _fetch_company_projects(cursor, company_id: int):
    """Busca todos os projetos da empresa."""
    cursor.execute("""
        SELECT 
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            COALESCE(cp.status, 'planned') AS status,
            LOWER(COALESCE(cp.priority, 'normal')) AS priority,
            cp.responsible_id,
            cp.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.start_date,
            cp.end_date AS deadline_date,
            cp.estimated_hours,
            cp.worked_hours,
            cp.created_at,
            cp.updated_at,
            pl.name AS plan_name,
            co.name AS company_name
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies co ON co.id = cp.company_id
        WHERE cp.company_id = %s
    """, (company_id,))
    
    return cursor.fetchall()


def _fetch_projects_for_members(cursor, member_ids: Sequence[int]):
    """Busca projetos atribuÃ­dos a membros de equipe."""
    if not member_ids:
        return []
    
    member_tuple = tuple(member_ids)
    cursor.execute("""
        SELECT 
            cp.id,
            cp.company_id,
            cp.plan_id,
            cp.title,
            cp.description,
            COALESCE(cp.status, 'planned') AS status,
            LOWER(COALESCE(cp.priority, 'normal')) AS priority,
            cp.responsible_id,
            cp.executor_id,
            resp.name AS responsible_name,
            exec.name AS executor_name,
            cp.start_date,
            cp.end_date AS deadline_date,
            cp.estimated_hours,
            cp.worked_hours,
            cp.created_at,
            cp.updated_at,
            pl.name AS plan_name,
            co.name AS company_name
        FROM company_projects cp
        LEFT JOIN employees resp ON resp.id = cp.responsible_id
        LEFT JOIN employees exec ON exec.id = cp.executor_id
        LEFT JOIN plans pl ON pl.id = cp.plan_id
        LEFT JOIN companies co ON co.id = cp.company_id
        WHERE (cp.responsible_id = ANY(%(members)s) OR cp.executor_id = ANY(%(members)s))
    """, {"members": member_tuple})
    
    return cursor.fetchall()


def _fetch_company_processes(cursor, company_id: int):
    """Busca instÃ¢ncias de processos da empresa."""
    cursor.execute("""
        SELECT 
            pi.id,
            pi.company_id,
            pi.process_id,
            pi.title,
            pi.description,
            COALESCE(pi.status, 'pending') AS status,
            LOWER(COALESCE(pi.priority, 'normal')) AS priority,
            pi.due_date AS deadline_date,
            pi.estimated_hours,
            COALESCE(pi.worked_hours, pi.actual_hours) AS worked_hours,
            pi.created_at,
            pi.updated_at,
            pi.assigned_collaborators,
            pi.instance_code,
            pi.trigger_type
        FROM process_instances pi
        WHERE pi.company_id = %s
    """, (company_id,))
    
    return cursor.fetchall()


def _fetch_processes_for_employee(cursor, employee_id: int):
    """Busca processos onde o colaborador estÃ¡ designado."""
    company_id = _fetch_employee_company_id(cursor, employee_id)
    if company_id is None:
        return []
    
    rows = _fetch_company_processes(cursor, company_id)
    return [row for row in rows if _is_employee_in_process(row, {employee_id})]


def _fetch_processes_for_members(cursor, member_ids: Sequence[int]):
    """Busca processos associados aos membros de uma equipe."""
    if not member_ids:
        return []
    
    company_ids = _fetch_companies_for_members(cursor, member_ids)
    if not company_ids:
        return []
    
    member_set = set(member_ids)
    
    processes = []
    for company_id in company_ids:
        rows = _fetch_company_processes(cursor, company_id)
        processes.extend(row for row in rows if _is_employee_in_process(row, member_set))
    
    return processes


def _serialize_project_activity(row, employee_id: int, member_ids: Optional[Sequence[int]] = None) -> Dict:
    """Serializa projeto."""
    data = dict(row)
    deadline = _coerce_date(data.get('deadline_date'))
    created_dt = _coerce_datetime(data.get('created_at'))
    updated_dt = _coerce_datetime(data.get('updated_at'))
    estimated_hours = _safe_float(data.get('estimated_hours'))
    worked_hours = _safe_float(data.get('worked_hours'))
    
    flags = _deadline_flags(deadline, data.get('status'))
    assignment = _resolve_assignment(
        employee_id,
        data.get('responsible_id'),
        data.get('executor_id'),
        member_ids
    )
    
    return {
        'id': data.get('id'),
        'type': 'project',
        'title': data.get('title'),
        'description': data.get('description'),
        'status': (data.get('status') or 'planned').lower(),
        'priority': (data.get('priority') or 'normal').lower(),
        'priority_order': _priority_order((data.get('priority') or 'normal').lower()),
        'status_order': _status_order((data.get('status') or 'planned').lower()),
        'deadline': deadline.isoformat() if deadline else None,
        'deadline_label': _deadline_label(deadline, data.get('status')),
        'start_date': _date_to_iso(_coerce_date(data.get('start_date'))),
        'is_overdue': flags['is_overdue'],
        'is_today': flags['is_today'],
        'is_this_week': flags['is_this_week'],
        'filter_tags': _build_filter_tags(flags, data.get('status')),
        'estimated_hours': estimated_hours,
        'worked_hours': worked_hours,
        'progress_percent': _calc_progress(estimated_hours, worked_hours),
        'responsible_id': data.get('responsible_id'),
        'responsible_name': data.get('responsible_name'),
        'executor_id': data.get('executor_id'),
        'executor_name': data.get('executor_name'),
        'assignment': assignment,
        'company_id': data.get('company_id'),
        'company_name': data.get('company_name'),
        'plan_id': data.get('plan_id'),
        'plan_name': data.get('plan_name'),
        'created_at': _datetime_to_iso(created_dt),
        'updated_at': _datetime_to_iso(updated_dt),
        'deadline_sort_key': _deadline_sort_key(deadline),
        'created_sort_key': _datetime_sort_key(created_dt),
        'updated_sort_key': _datetime_sort_key(updated_dt)
    }


def _serialize_process_activity(row, employee_id: int, member_ids: Optional[Sequence[int]] = None) -> Dict:
    """Serializa instÃ¢ncia de processo."""
    data = dict(row)
    deadline = _coerce_date(data.get('deadline_date'))
    created_dt = _coerce_datetime(data.get('created_at'))
    updated_dt = _coerce_datetime(data.get('updated_at'))
    estimated_hours = _safe_float(data.get('estimated_hours'))
    worked_hours = _safe_float(data.get('worked_hours'))
    
    flags = _deadline_flags(deadline, data.get('status'))
    collaborators = _parse_collaborators(data.get('assigned_collaborators'))
    assignment = _resolve_process_assignment(employee_id, collaborators, member_ids)
    
    return {
        'id': data.get('id'),
        'type': 'process',
        'title': data.get('title'),
        'description': data.get('description'),
        'status': (data.get('status') or 'pending').lower(),
        'priority': (data.get('priority') or 'normal').lower(),
        'priority_order': _priority_order((data.get('priority') or 'normal').lower()),
        'status_order': _status_order((data.get('status') or 'pending').lower()),
        'deadline': deadline.isoformat() if deadline else None,
        'deadline_label': _deadline_label(deadline, data.get('status')),
        'is_overdue': flags['is_overdue'],
        'is_today': flags['is_today'],
        'is_this_week': flags['is_this_week'],
        'filter_tags': _build_filter_tags(flags, data.get('status')),
        'estimated_hours': estimated_hours,
        'worked_hours': worked_hours,
        'progress_percent': _calc_progress(estimated_hours, worked_hours),
        'assignment': assignment,
        'company_id': data.get('company_id'),
        'created_at': _datetime_to_iso(created_dt),
        'updated_at': _datetime_to_iso(updated_dt),
        'deadline_sort_key': _deadline_sort_key(deadline),
        'created_sort_key': _datetime_sort_key(created_dt),
        'updated_sort_key': _datetime_sort_key(updated_dt),
        'instance_code': data.get('instance_code'),
        'trigger_type': data.get('trigger_type'),
        'collaborators': collaborators
    }


def _apply_filters(activities: List[Dict], filters: Dict) -> List[Dict]:
    """Aplica filtros e busca."""
    if not activities:
        return []
    
    filter_type = (filters.get('filter') or 'all').lower()
    search_term = (filters.get('search') or '').strip().lower()
    
    filtered = activities
    
    if filter_type != 'all':
        filtered = [
            activity for activity in filtered
            if filter_type in activity.get('filter_tags', [])
        ]
    
    if search_term:
        filtered = [
            activity for activity in filtered
            if search_term in ' '.join(filter(None, [
                activity.get('title', '').lower(),
                activity.get('description', '').lower(),
                activity.get('plan_name', '').lower(),
                activity.get('company_name', '').lower()
            ]))
        ]
    
    return filtered


def _apply_sort(activities: List[Dict], sort_by: str) -> List[Dict]:
    """Ordena atividades."""
    sort_by = (sort_by or 'deadline').lower()
    
    if sort_by == 'priority':
        key_fn = lambda activity: (
            -activity.get('priority_order', 0),
            activity.get('deadline_sort_key', 9999999)
        )
    elif sort_by == 'status':
        key_fn = lambda activity: activity.get('status_order', 99)
    elif sort_by == 'recent':
        key_fn = lambda activity: -activity.get('updated_sort_key', activity.get('created_sort_key', 0))
    else:
        key_fn = lambda activity: (
            activity.get('deadline_sort_key', 9999999),
            -activity.get('priority_order', 0)
        )
    
    return sorted(activities, key=key_fn)


def _calculate_stats_from_activities(activities: List[Dict]) -> Dict:
    """Gera contadores de status."""
    stats = {
        'pending': 0,
        'in_progress': 0,
        'overdue': 0,
        'completed': 0
    }
    
    for activity in activities:
        status = (activity.get('status') or '').lower()
        if status in ('completed', 'done'):
            stats['completed'] += 1
        elif status in ('in_progress', 'executing', 'ongoing'):
            stats['in_progress'] += 1
        else:
            stats['pending'] += 1
        
        if activity.get('is_overdue') and status != 'completed':
            stats['overdue'] += 1
    
    return stats


def _count_my_activities(cursor, employee_id: int) -> int:
    """Conta atividades pessoais."""
    return len(_fetch_projects_for_employee(cursor, employee_id)) + len(_fetch_processes_for_employee(cursor, employee_id))


def _count_team_activities(cursor, employee_id: int) -> int:
    """Conta atividades da equipe."""
    member_ids = _fetch_team_member_ids(cursor, employee_id)
    if not member_ids:
        return 0
    
    return len(_fetch_projects_for_members(cursor, member_ids)) + len(_fetch_processes_for_members(cursor, member_ids))


def _count_company_activities(cursor, employee_id: int) -> int:
    """Conta atividades da empresa."""
    company_id = _fetch_employee_company_id(cursor, employee_id)
    if company_id is None:
        return 0
    
    return len(_fetch_company_projects(cursor, company_id)) + len(_fetch_company_processes(cursor, company_id))


def _fetch_team_member_ids(cursor, employee_id: int) -> List[int]:
    """Retorna IDs dos membros da equipe."""
    cursor.execute("""
        SELECT team_id
        FROM team_members
        WHERE employee_id = %s
        LIMIT 1
    """, (employee_id,))
    
    row = cursor.fetchone()
    if not row:
        return []
    
    team_id = row[0]
    
    cursor.execute("""
        SELECT employee_id
        FROM team_members
        WHERE team_id = %s
    """, (team_id,))
    
    return [member_row[0] for member_row in cursor.fetchall()]


def _fetch_employee_company_id(cursor, employee_id: int) -> Optional[int]:
    """ObtÃ©m company_id do colaborador."""
    cursor.execute("SELECT company_id FROM employees WHERE id = %s", (employee_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def _fetch_companies_for_members(cursor, member_ids: Sequence[int]) -> List[int]:
    """ObtÃ©m empresas vinculadas aos membros."""
    cursor.execute(
        """
        SELECT DISTINCT company_id
        FROM employees
        WHERE id = ANY(%(members)s)
        """,
        {"members": tuple(member_ids)},
    )
    
    return [row[0] for row in cursor.fetchall()]


def _is_employee_in_process(row, member_ids: set) -> bool:
    """Verifica se algum membro estÃ¡ associado a um processo."""
    collaborators = _parse_collaborators(row.get('assigned_collaborators'))
    collaborator_ids = {collab.get('id') for collab in collaborators if collab.get('id') is not None}
    return bool(member_ids & collaborator_ids)


def _parse_collaborators(raw_value) -> List[Dict]:
    """Converte campo de colaboradores em lista."""
    if not raw_value:
        return []
    
    if isinstance(raw_value, list):
        return raw_value
    
    if isinstance(raw_value, str):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return []
    
    return []


def _resolve_assignment(employee_id: int, responsible_id: Optional[int], executor_id: Optional[int], member_ids: Optional[Sequence[int]]) -> Dict:
    """Determina o papel do colaborador em um projeto."""
    assignment = {'type': None, 'label': None}
    
    if employee_id and executor_id == employee_id:
        assignment.update({'type': 'executor', 'label': 'âš™ï¸ Executor'})
    elif employee_id and responsible_id == employee_id:
        assignment.update({'type': 'responsible', 'label': 'ðŸ‘¤ ResponsÃ¡vel'})
    elif member_ids and (responsible_id in member_ids or executor_id in member_ids):
        assignment.update({'type': 'team', 'label': 'ðŸ‘¥ Equipe'})
    
    return assignment


def _resolve_process_assignment(employee_id: int, collaborators: List[Dict], member_ids: Optional[Sequence[int]]) -> Dict:
    """Determina o papel do colaborador em um processo."""
    collaborator_ids = {collab.get('id') for collab in collaborators if collab.get('id') is not None}
    assignment = {'type': None, 'label': None}
    
    if employee_id in collaborator_ids:
        assignment.update({'type': 'assigned', 'label': 'âš™ï¸ Executor'})
    elif member_ids and collaborator_ids.intersection(member_ids):
        assignment.update({'type': 'team', 'label': 'ðŸ‘¥ Equipe'})
    
    return assignment


def _deadline_flags(deadline: Optional[date], status: Optional[str]) -> Dict[str, bool]:
    """Calcula flags de prazo."""
    today = date.today()
    flags = {'is_today': False, 'is_overdue': False, 'is_this_week': False}
    
    if not deadline:
        return flags
    
    delta = (deadline - today).days
    status = (status or '').lower()
    
    flags['is_today'] = delta == 0
    flags['is_overdue'] = delta < 0 and status != 'completed'
    flags['is_this_week'] = 0 <= delta <= 7
    
    return flags


def _build_filter_tags(flags: Dict[str, bool], status: Optional[str]) -> List[str]:
    """Lista tags de filtro."""
    tags = ['all']
    if flags.get('is_today'):
        tags.append('today')
    if flags.get('is_this_week'):
        tags.append('week')
    if flags.get('is_overdue'):
        tags.append('overdue')
    
    status = (status or '').lower()
    if status and status not in tags:
        tags.append(status)
    
    return tags


def _deadline_label(deadline: Optional[date], status: Optional[str]) -> Optional[str]:
    """Texto amigÃ¡vel de prazo."""
    if not deadline:
        return None
    
    today = date.today()
    delta = (deadline - today).days
    
    if delta == 0:
        return 'Hoje'
    if delta == 1:
        return 'AmanhÃ£'
    if delta == -1:
        return 'Ontem'
    if delta > 1:
        return f'Em {delta} dias'
    
    status = (status or '').lower()
    if status == 'completed':
        return f'ConcluÃ­do hÃ¡ {-delta} dias'
    
    return f'Atrasado {abs(delta)} dias'


def _calc_progress(estimated: float, worked: float) -> int:
    """Calcula percentual de progresso."""
    if not estimated:
        return 0
    progress = (worked / estimated) * 100
    return max(0, min(int(round(progress)), 100))


def _safe_float(value: Any) -> float:
    """Converte valores em float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_date(value: Any) -> Optional[date]:
    """Converte valor em date."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _coerce_datetime(value: Any) -> Optional[datetime]:
    """Converte valor em datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def _datetime_to_iso(value: Optional[datetime]) -> Optional[str]:
    """Formata datetime em ISO8601."""
    if not value:
        return None
    return value.isoformat()


def _date_to_iso(value: Optional[date]) -> Optional[str]:
    """Formata date em ISO."""
    if not value:
        return None
    return value.isoformat()


def _deadline_sort_key(deadline: Optional[date]) -> int:
    """Chave de ordenaÃ§Ã£o por prazo."""
    return deadline.toordinal() if deadline else 9999999


def _datetime_sort_key(value: Optional[datetime]) -> int:
    """Chave de ordenaÃ§Ã£o por data/hora."""
    if not value:
        return 0
    return int(value.timestamp())


def _can_view_company(cursor, employee_id: int) -> bool:
    """Verifica se employee tem permissÃ£o para ver atividades da empresa"""
    
    # TODO: Implementar verificaÃ§Ã£o de role/permissÃ£o
    # Por enquanto, permitir para todos (demo)
    return True


def _priority_order(priority: str) -> int:
    """Ordem de prioridade para ordenaÃ§Ã£o"""
    order = {'urgent': 4, 'high': 3, 'normal': 2, 'low': 1}
    return order.get(priority, 0)


def _status_order(status: str) -> int:
    """Ordem de status para ordenaÃ§Ã£o"""
    order = {'overdue': 1, 'pending': 2, 'planned': 3, 'in_progress': 4, 'executing': 5, 'completed': 6}
    return order.get(status, 99)


# ============================================================================
# WORK HOURS
# ============================================================================

def add_work_hours(employee_id: int, activity_type: str, activity_id: int, work_data: Dict) -> Dict:
    """
    Adiciona registro de horas trabalhadas
    
    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        work_data: {work_date, hours, description}
    
    Returns:
        Dict com log criado
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar nome do employee
        cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
        employee_row = cursor.fetchone()
        employee_name = employee_row[0] if employee_row else "Desconhecido"
        
        # Inserir log
        cursor.execute("""
            INSERT INTO activity_work_logs 
            (activity_type, activity_id, employee_id, employee_name, work_date, hours_worked, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            activity_type,
            activity_id,
            employee_id,
            employee_name,
            work_data['work_date'],
            work_data['hours'],
            work_data.get('description')
        ))
        
        log_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return {
            'id': log_id,
            'success': True,
            'message': f'{work_data["hours"]}h registradas com sucesso'
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def add_comment(employee_id: int, activity_type: str, activity_id: int, comment_data: Dict) -> Dict:
    """
    Adiciona comentÃ¡rio em atividade
    
    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        comment_data: {comment_type, comment, is_private}
    
    Returns:
        Dict com comentÃ¡rio criado
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar nome do employee
        cursor.execute("SELECT name FROM employees WHERE id = %s", (employee_id,))
        employee_row = cursor.fetchone()
        employee_name = employee_row[0] if employee_row else "Desconhecido"
        
        # Inserir comentÃ¡rio
        cursor.execute("""
            INSERT INTO activity_comments 
            (activity_type, activity_id, employee_id, employee_name, comment_type, comment_text, is_private)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            activity_type,
            activity_id,
            employee_id,
            employee_name,
            comment_data.get('comment_type', 'note'),
            comment_data['comment'],
            comment_data.get('is_private', False)
        ))
        
        comment_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return {
            'id': comment_id,
            'success': True,
            'message': 'ComentÃ¡rio adicionado com sucesso'
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def complete_activity(employee_id: int, activity_type: str, activity_id: int, completion_data: Dict) -> Dict:
    """
    Finaliza atividade
    
    Args:
        employee_id: ID do colaborador
        activity_type: 'project' ou 'process'
        activity_id: ID da atividade
        completion_data: {completion_comment (optional)}
    
    Returns:
        Dict com resultado
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Adicionar comentÃ¡rio final se fornecido
        if completion_data.get('completion_comment'):
            add_comment(employee_id, activity_type, activity_id, {
                'comment_type': 'note',
                'comment': completion_data['completion_comment'],
                'is_private': False
            })
        
        # Atualizar status
        if activity_type == 'project':
            cursor.execute("""
                UPDATE company_projects
                SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (activity_id,))
        elif activity_type == 'process':
            cursor.execute("""
                UPDATE process_instances
                SET status = 'completed', 
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (activity_id,))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Atividade finalizada com sucesso'
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


# ============================================================================
# TEAM OVERVIEW
# ============================================================================

def get_team_overview(employee_id: int) -> Dict:
    """
    Retorna dados para o Team Overview
    
    Returns:
        Dict com distribuiÃ§Ã£o, alertas e performance
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Buscar equipe
        cursor.execute("""
            SELECT t.id, t.name, t.description
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.id
            WHERE tm.employee_id = %s
            LIMIT 1
        """, (employee_id,))
        
        team_row = cursor.fetchone()
        if not team_row:
            conn.close()
            return {}
        
        team_id = team_row[0]
        team_name = team_row[1]
        
        # Buscar distribuiÃ§Ã£o de carga
        distribution = _get_team_load_distribution(cursor, team_id)
        
        # Gerar alertas
        alerts = _generate_team_alerts(distribution)
        
        # Calcular performance
        performance = _calculate_team_performance(cursor, team_id)
        
        conn.close()
        
        return {
            'team_name': team_name,
            'members': distribution,
            'alerts': alerts,
            'performance': performance
        }
        
    except Exception as e:
        conn.close()
        raise e


def _get_team_load_distribution(cursor, team_id: int) -> List[Dict]:
    """Calcula distribuiÃ§Ã£o de carga entre membros"""
    
    cursor.execute("""
        SELECT 
            e.id,
            e.name,
            tm.role,
            COALESCE(
                (SELECT SUM(estimated_hours) 
                 FROM company_projects 
                 WHERE (responsible_id = e.id OR executor_id = e.id) 
                 AND status != 'completed'), 
                0
            ) as allocated_hours,
            COALESCE(
                (SELECT SUM(worked_hours) 
                 FROM company_projects 
                 WHERE (responsible_id = e.id OR executor_id = e.id)), 
                0
            ) as worked_hours
        FROM team_members tm
        JOIN employees e ON e.id = tm.employee_id
        WHERE tm.team_id = %s
        ORDER BY allocated_hours DESC
    """, (team_id,))
    
    members = []
    for row in cursor.fetchall():
        capacity = 40  # TODO: Buscar capacidade configurada do employee
        allocated = float(row[3] or 0)
        utilization = (allocated / capacity * 100) if capacity > 0 else 0
        
        members.append({
            'id': row[0],
            'name': row[1],
            'role': row[2],
            'capacity': capacity,
            'allocated': allocated,
            'worked': float(row[4] or 0),
            'utilization_percent': round(utilization),
            'status': _get_load_status(utilization)
        })
    
    return members


def _get_load_status(utilization: float) -> str:
    """Determina status baseado na utilizaÃ§Ã£o"""
    if utilization > 90:
        return 'overload'
    elif utilization > 75:
        return 'high'
    elif utilization < 50:
        return 'available'
    else:
        return 'normal'


def _generate_team_alerts(members: List[Dict]) -> List[Dict]:
    """Gera alertas baseado na distribuiÃ§Ã£o"""
    alerts = []
    
    for member in members:
        if member['status'] == 'overload':
            alerts.append({
                'type': 'overload',
                'severity': 'warning',
                'employee_id': member['id'],
                'employee_name': member['name'],
                'message': f"{member['name']} sobrecarregado(a)",
                'details': f"{member['allocated']}h alocadas ({member['utilization_percent']}% da capacidade)"
            })
        elif member['status'] == 'available':
            alerts.append({
                'type': 'available',
                'severity': 'success',
                'employee_id': member['id'],
                'employee_name': member['name'],
                'message': f"{member['name']} disponÃ­vel",
                'details': f"{member['capacity'] - member['allocated']}h de capacidade livre"
            })
    
    return alerts


def _calculate_team_performance(cursor, team_id: int) -> Dict:
    """Calcula mÃ©tricas de performance da equipe"""
    
    # TODO: Implementar cÃ¡lculo real
    return {
        'avg_score': 78,
        'completion_rate': 85,
        'capacity_utilization': 75
    }


# ============================================================================
# COMPANY OVERVIEW
# ============================================================================

def get_company_overview(employee_id: int) -> Dict:
    """
    Retorna dados executivos para Company Overview
    
    Returns:
        Dict com mÃ©tricas executivas
    """
    conn = pg_connect()
    cursor = conn.cursor()
    
    try:
        # Verificar permissÃ£o
        if not _can_view_company(cursor, employee_id):
            raise PermissionError("Sem permissÃ£o para visualizar dados da empresa")
        
        # Buscar company_id
        cursor.execute("SELECT company_id FROM employees WHERE id = %s", (employee_id,))
        company_id = cursor.fetchone()[0]
        
        # Buscar mÃ©tricas
        summary = _get_company_summary(cursor, company_id)
        heatmap = _get_company_heatmap(cursor, company_id)
        ranking = _get_department_ranking(cursor, company_id)
        
        conn.close()
        
        return {
            'summary': summary,
            'heatmap': heatmap,
            'ranking': ranking
        }
        
    except Exception as e:
        conn.close()
        raise e


def _get_company_summary(cursor, company_id: int) -> Dict:
    """MÃ©tricas gerais da empresa"""
    
    # Contar equipes
    cursor.execute("SELECT COUNT(*) FROM teams WHERE company_id = %s AND is_active = true", (company_id,))
    teams_count = cursor.fetchone()[0]
    
    # Contar colaboradores
    cursor.execute("SELECT COUNT(*) FROM employees WHERE company_id = %s", (company_id,))
    employees_count = cursor.fetchone()[0]
    
    # Contar atividades
    cursor.execute("SELECT COUNT(*) FROM company_projects WHERE company_id = %s AND status != 'completed'", (company_id,))
    activities_count = cursor.fetchone()[0]
    
    return {
        'active_teams': teams_count,
        'total_employees': employees_count,
        'avg_capacity_utilization': 78,  # TODO: Calcular real
        'total_activities': activities_count
    }


def _get_company_heatmap(cursor, company_id: int) -> List[Dict]:
    """Mapa de calor por equipe/departamento"""
    
    # TODO: Implementar query real agrupando por equipe
    # Mockado por enquanto
    return [
        {
            'team_name': 'Comercial',
            'employee_count': 12,
            'activities_count': 45,
            'utilization_percent': 92,
            'status': 'high'
        },
        {
            'team_name': 'TI / Tecnologia',
            'employee_count': 18,
            'activities_count': 65,
            'utilization_percent': 75,
            'status': 'medium'
        },
        {
            'team_name': 'RH / Administrativo',
            'employee_count': 8,
            'activities_count': 18,
            'utilization_percent': 48,
            'status': 'low'
        },
        {
            'team_name': 'OperaÃ§Ãµes',
            'employee_count': 25,
            'activities_count': 52,
            'utilization_percent': 98,
            'status': 'critical'
        }
    ]


def _get_department_ranking(cursor, company_id: int) -> List[Dict]:
    """Ranking de performance por departamento"""
    
    # TODO: Implementar query real
    return [
        {'rank': 1, 'team_name': 'TI / Tecnologia', 'score': 85, 'completion_rate': 92},
        {'rank': 2, 'team_name': 'Comercial', 'score': 82, 'completion_rate': 88},
        {'rank': 3, 'team_name': 'OperaÃ§Ãµes', 'score': 78, 'completion_rate': 85},
        {'rank': 4, 'team_name': 'RH / Administrativo', 'score': 75, 'completion_rate': 80}
    ]




