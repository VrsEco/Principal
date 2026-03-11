from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from models import Occurrence, Portfolio, Project, ProjectActivityCollaborator, ProjectTask


def format_date_br(value: Any) -> str:
    if not value:
        return 'Não definido'
    if hasattr(value, 'strftime'):
        return value.strftime('%d/%m/%Y')
    try:
        return datetime.fromisoformat(str(value)).strftime('%d/%m/%Y')
    except Exception:
        return str(value)



def normalize_text(value: Any, fallback: str = 'Não informado') -> str:
    normalized = str(value or '').strip()
    return normalized or fallback



def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default



def coerce_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None



def task_diary_rows(task: ProjectTask) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    logs = task.logs or []
    if not isinstance(logs, list):
        return rows
    for item in logs:
        if not isinstance(item, dict):
            continue
        date_label = normalize_text(item.get('timestamp') or item.get('date') or item.get('created_at'), 'Sem data')
        description = normalize_text(item.get('content') or item.get('text') or item.get('message'), 'Sem descrição')
        rows.append((date_label, description))
    return rows



def task_collaborators(task: ProjectTask) -> list[dict[str, Any]]:
    collaborators = (
        ProjectActivityCollaborator.query.filter_by(activity_id=task.id, is_deleted=False)
        .order_by(ProjectActivityCollaborator.created_at.asc())
        .all()
    )
    data: list[dict[str, Any]] = []
    for collab in collaborators:
        data.append({
            'employee_name': collab.employee.name if collab.employee else 'Colaborador',
            'worked_hours': to_float(collab.worked_hours),
            'estimated_hours': to_float(collab.estimated_hours),
            'notes': normalize_text(collab.notes, '-'),
        })
    if not data:
        data.append({
            'employee_name': normalize_text(task.employee_name, 'Sem responsável'),
            'worked_hours': to_float(task.worked_hours),
            'estimated_hours': to_float(task.estimated_hours),
            'notes': 'Responsável principal',
        })
    return data



def task_occurrences(task: ProjectTask) -> list[Occurrence]:
    if not task.project:
        return []
    occurrences = (
        Occurrence.query.filter_by(company_id=task.project.company_id, project_id=task.project_id)
        .order_by(Occurrence.created_at.desc())
        .all()
    )
    collaborator_ids = {
        collab.employee_id
        for collab in ProjectActivityCollaborator.query.filter_by(activity_id=task.id, is_deleted=False).all()
        if collab.employee_id
    }
    if task.employee_id:
        collaborator_ids.add(task.employee_id)
    if not collaborator_ids:
        return occurrences

    filtered: list[Occurrence] = []
    for occurrence in occurrences:
        if occurrence.employee_id in collaborator_ids or occurrence.employee_id is None:
            filtered.append(occurrence)
            continue
        ids = occurrence.collaborators_ids or []
        if isinstance(ids, list) and collaborator_ids.intersection({int(value) for value in ids if value is not None}):
            filtered.append(occurrence)
    return filtered



def summarize_occurrences(occurrences: list[Occurrence]) -> dict[str, Any]:
    summary = {
        'positive': {'count': 0, 'score': 0},
        'negative': {'count': 0, 'score': 0},
        'total_score': 0,
    }
    for occurrence in occurrences:
        occ_type = (occurrence.type or '').lower().strip()
        if occ_type not in {'positive', 'negative'}:
            continue
        score = int(occurrence.score or 0)
        summary[occ_type]['count'] += 1
        summary[occ_type]['score'] += score
        summary['total_score'] += score
    return summary



def project_occurrence_summary(project: Project) -> dict[str, Any]:
    occurrences = Occurrence.query.filter_by(company_id=project.company_id, project_id=project.id).all()
    return summarize_occurrences(occurrences)



def portfolio_occurrence_summary(portfolio: Portfolio) -> dict[str, Any]:
    project_ids = [row[0] for row in Project.query.with_entities(Project.id).filter_by(company_id=portfolio.company_id, portfolio_id=portfolio.id).all()]
    if not project_ids:
        return summarize_occurrences([])
    occurrences = Occurrence.query.filter(Occurrence.company_id == portfolio.company_id, Occurrence.project_id.in_(project_ids)).all()
    return summarize_occurrences(occurrences)



def task_occurrence_summary(task: ProjectTask) -> dict[str, Any]:
    return summarize_occurrences(task_occurrences(task))



def task_completion_percent(task: ProjectTask) -> int:
    estimated = to_float(task.estimated_hours)
    worked = to_float(task.worked_hours)
    stage = (task.stage or task.status or '').lower()
    if estimated > 0:
        return max(0, min(int(round((worked / estimated) * 100)), 100))
    if stage == 'completed':
        return 100
    if stage in {'executing', 'in_progress'}:
        return 60
    if stage in {'pending', 'waiting'}:
        return 25
    return 0



def task_deadline_score(task: ProjectTask) -> int:
    due_date = coerce_date(getattr(task, 'due_date', None))
    completion_date = coerce_date(getattr(task, 'completion_date', None))
    today = datetime.now().date()
    reference = completion_date or today
    if not due_date:
        return 80
    delay_days = max((reference - due_date).days, 0)
    if delay_days == 0:
        return 100 if (task.stage or task.status) == 'completed' else 85
    return max(0, 100 - (delay_days * 10))



def calculate_task_score(task: ProjectTask) -> float:
    occurrence = task_occurrence_summary(task)
    completion_rate = task_completion_percent(task)
    deadline_score = task_deadline_score(task)
    occurrence_score = max(0, min(100, 50 + int(occurrence['total_score'])))
    return round((completion_rate * 0.35) + (deadline_score * 0.45) + (occurrence_score * 0.2), 1)



def calculate_project_score(project: Project) -> int:
    stats = project.task_stats
    total = int(stats.get('total', 0))
    completed = int(stats.get('completed', 0))
    open_total = int(stats.get('open', 0))
    delayed = int(stats.get('delayed', 0))
    completion_rate = int(round((completed / total) * 100)) if total else 0
    overdue_penalty = min((delayed / open_total), 1.0) if open_total else 0.0
    deadline_score = max(0, 100 - int(round(overdue_penalty * 100)))
    occurrence = project_occurrence_summary(project)
    occurrence_score = max(0, min(100, 50 + int(occurrence['total_score'])))
    return max(0, min(int(round((completion_rate * 0.35) + (deadline_score * 0.45) + (occurrence_score * 0.2))), 100))



def calculate_portfolio_score(portfolio: Portfolio) -> int:
    projects = Project.query.filter_by(company_id=portfolio.company_id, portfolio_id=portfolio.id).all()
    if not projects:
        return 0
    return int(round(sum(calculate_project_score(project) for project in projects) / len(projects)))



def format_incident_score(score: int) -> str:
    prefix = '+' if score > 0 else ''
    return f'{prefix}{score} pts'



def format_occurrence_summary(summary: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ('Ocorrências positivas', f"{summary['positive']['count']} | {format_incident_score(int(summary['positive']['score']))}"),
        ('Ocorrências negativas', f"{summary['negative']['count']} | {format_incident_score(int(summary['negative']['score']))}"),
        ('Resultado ocorrências', format_incident_score(int(summary['total_score']))),
    ]



def aggregate_project_hours(project: Project) -> tuple[list[dict[str, Any]], float, float]:
    tasks = project.tasks.order_by(ProjectTask.id.asc()).all()
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {'employee_name': '', 'estimated_hours': 0.0, 'worked_hours': 0.0})
    estimated_total = 0.0
    worked_total = 0.0

    for task in tasks:
        collaborators = [collab for collab in task.collaborators if not getattr(collab, 'is_deleted', False)]
        if collaborators:
            task_estimated = 0.0
            task_worked = 0.0
            for collab in collaborators:
                name = collab.employee.name if collab.employee else 'Colaborador'
                bucket = buckets[name]
                bucket['employee_name'] = name
                bucket['estimated_hours'] += to_float(collab.estimated_hours)
                bucket['worked_hours'] += to_float(collab.worked_hours)
                task_estimated += to_float(collab.estimated_hours)
                task_worked += to_float(collab.worked_hours)
            estimated_total += task_estimated
            worked_total += task_worked
            continue

        name = normalize_text(task.employee_name, 'Sem responsável')
        bucket = buckets[name]
        bucket['employee_name'] = name
        bucket['estimated_hours'] += to_float(task.estimated_hours)
        bucket['worked_hours'] += to_float(task.worked_hours)
        estimated_total += to_float(task.estimated_hours)
        worked_total += to_float(task.worked_hours)

    rows = sorted(buckets.values(), key=lambda item: item['employee_name'].lower())
    return rows, estimated_total, worked_total



def aggregate_portfolio_hours(portfolio: Portfolio) -> tuple[list[dict[str, Any]], float, float, float]:
    projects = Project.query.filter_by(company_id=portfolio.company_id, portfolio_id=portfolio.id).all()
    buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {'employee_name': '', 'estimated_hours': 0.0, 'worked_hours': 0.0})
    estimated_total = 0.0
    worked_total = 0.0
    progress_sum = 0.0

    for project in projects:
        rows, project_estimated, project_worked = aggregate_project_hours(project)
        for row in rows:
            bucket = buckets[row['employee_name']]
            bucket['employee_name'] = row['employee_name']
            bucket['estimated_hours'] += to_float(row['estimated_hours'])
            bucket['worked_hours'] += to_float(row['worked_hours'])
        estimated_total += project_estimated
        worked_total += project_worked
        progress_sum += float(project.task_stats.get('progress', 0))

    avg_progress = (progress_sum / len(projects)) if projects else 0.0
    rows = sorted(buckets.values(), key=lambda item: item['employee_name'].lower())
    return rows, estimated_total, worked_total, avg_progress



def build_header_rows_project(project: Project, estimated_total: float, worked_total: float) -> list[tuple[str, str]]:
    stats = project.task_stats
    occurrence = project_occurrence_summary(project)
    return [
        ('Portfólio', normalize_text(getattr(project.portfolio, 'name', None), 'Não vinculado')),
        ('Responsável', normalize_text(project.owner, 'Não definido')),
        ('Status', normalize_text(project.status)),
        ('Prazo', format_date_br(project.deadline)),
        ('% de conclusão', f"{int(stats.get('progress', 0))}%"),
        ('Horas previstas', f'{estimated_total:.1f}h'),
        ('Horas realizadas', f'{worked_total:.1f}h'),
        *format_occurrence_summary(occurrence),
        ('Observações', normalize_text(project.notes)),
    ]



def build_header_rows_portfolio(portfolio: Portfolio, estimated_total: float, worked_total: float, avg_progress: float) -> list[tuple[str, str]]:
    occurrence = portfolio_occurrence_summary(portfolio)
    project_count = Project.query.filter_by(company_id=portfolio.company_id, portfolio_id=portfolio.id).count()
    return [
        ('Responsável', normalize_text(getattr(portfolio.responsible, 'name', None), 'Não definido')),
        ('Projetos vinculados', str(project_count)),
        ('% médio de conclusão', f'{avg_progress:.0f}%'),
        ('Horas previstas', f'{estimated_total:.1f}h'),
        ('Horas realizadas', f'{worked_total:.1f}h'),
        *format_occurrence_summary(occurrence),
        ('Observações', normalize_text(portfolio.notes)),
    ]
