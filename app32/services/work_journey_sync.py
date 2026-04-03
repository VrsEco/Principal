from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from models import (
    db,
    Employee,
    Meeting,
    ProcessInstance,
    ProcessInstanceCollaborator,
    ProjectTask,
    WorkJourneyAbsenceRequest,
    WorkJourneyItem,
    WorkJourneyRule,
)
from services.routine_journey_binding_service import get_bound_block_id
from services.work_journey_base import ACTIVE_ITEM_STATUSES, ensure_employee
from services.work_journey_helpers import PRIORITY_ORDER, date_range, rule_matches_date


def load_period_items(company_id: int, employee_id: int, period_start: date, period_end: date) -> list[WorkJourneyItem]:
    return (
        WorkJourneyItem.query.filter(
            WorkJourneyItem.company_id == company_id,
            WorkJourneyItem.employee_id == employee_id,
            WorkJourneyItem.rule_id.is_(None),
            or_(
                WorkJourneyItem.occurrence_date.between(period_start, period_end),
                WorkJourneyItem.due_date.between(period_start, period_end),
                and_(WorkJourneyItem.due_date < period_start, WorkJourneyItem.status.in_(list(ACTIVE_ITEM_STATUSES))),
            ),
        )
        .order_by(WorkJourneyItem.due_date.asc().nulls_last(), WorkJourneyItem.priority.desc(), WorkJourneyItem.id.asc())
        .all()
    )


def sync_rule_occurrences(company_id: int, employee_id: int, period_start: date, period_end: date) -> None:
    approved_absences = (
        WorkJourneyAbsenceRequest.query.filter_by(company_id=company_id, employee_id=employee_id, status='approved')
        .filter(WorkJourneyAbsenceRequest.start_date <= period_end)
        .filter(WorkJourneyAbsenceRequest.end_date >= period_start)
        .all()
    )
    rules = (
        WorkJourneyRule.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True)
        .order_by(WorkJourneyRule.id.asc())
        .all()
    )
    for rule in rules:
        for current in date_range(period_start, period_end):
            if any(absence.start_date <= current <= absence.end_date for absence in approved_absences):
                continue
            if rule.start_date and current < rule.start_date:
                continue
            if rule.end_date and current > rule.end_date:
                continue
            if not rule_matches_date(rule.recurrence_type, rule.recurrence_config or {}, current):
                continue
            item = WorkJourneyItem.query.filter_by(company_id=company_id, rule_id=rule.id, occurrence_date=current).first()
            if not item:
                item = WorkJourneyItem(company_id=company_id, employee_id=employee_id, rule_id=rule.id, occurrence_date=current)
            item.block_id = item.block_id or rule.preferred_block_id
            item.item_type = rule.item_type
            item.title = rule.title
            item.description = rule.description
            item.recurrence_type = rule.recurrence_type
            item.due_date = current
            item.estimated_minutes = int(rule.estimated_minutes or 0)
            item.priority = rule.priority
            item.metadata_json = dict(item.metadata_json or {})
            item.metadata_json.setdefault('source_label', 'Regra recorrente')
            db.session.add(item)


def sync_process_instances(company_id: int, employee_id: int, period_start: date, period_end: date) -> None:
    collaborator_ids = [
        row.process_instance_id
        for row in ProcessInstanceCollaborator.query.filter_by(employee_id=employee_id, is_deleted=False).all()
    ]
    query = (
        ProcessInstance.query.options(joinedload(ProcessInstance.process_rel), joinedload(ProcessInstance.routine))
        .filter(ProcessInstance.company_id == company_id)
        .filter(
            or_(
                ProcessInstance.executor_id == employee_id,
                ProcessInstance.responsible_id == employee_id,
                ProcessInstance.owner_employee_id == employee_id,
                ProcessInstance.id.in_(collaborator_ids or [-1]),
            )
        )
        .filter(
            or_(
                ProcessInstance.due_date.between(period_start, period_end),
                and_(ProcessInstance.due_date < period_start, ProcessInstance.status.in_(['pending', 'in_progress', 'overdue'])),
            )
        )
        .all()
    )
    for instance in query:
        metadata = {
            'source_label': 'Instância de processo',
            'source_code': instance.instance_code,
            'process_id': instance.process_id,
            'routine_id': instance.routine_id,
            'process_name': instance.process_rel.name if instance.process_rel else None,
            'process_code': instance.process_rel.code if instance.process_rel else None,
            'manual_assignment': current_manual_assignment(company_id, 'process_instance', instance.id),
            'source_url': f"/process-map/process/{instance.process_id}?tab=routines" if instance.process_id else None,
        }
        recurrence_type = getattr(instance.routine, 'schedule_type', None) if instance.routine else None
        bound_block_id = get_bound_block_id(company_id, instance.routine_id, employee_id)
        upsert_source_item(
            company_id=company_id,
            employee_id=employee_id,
            item_type='process_instance',
            source_id=instance.id,
            title=instance.title,
            description=instance.description,
            due_date=instance.due_date,
            estimated_minutes=int(float(instance.estimated_hours or 0) * 60),
            worked_minutes=int(float(instance.actual_hours or instance.worked_hours or 0) * 60),
            priority=str(instance.priority or 'normal'),
            status=normalize_source_status(instance.status),
            recurrence_type=recurrence_type,
            bound_block_id=bound_block_id,
            metadata=metadata,
        )


def sync_project_tasks(company_id: int, employee_id: int, period_start: date, period_end: date) -> None:
    tasks = (
        ProjectTask.query.options(joinedload(ProjectTask.project))
        .filter(ProjectTask.employee_id == employee_id)
        .filter(ProjectTask.project.has(company_id=company_id))
        .filter(
            or_(
                ProjectTask.due_date.between(period_start, period_end),
                and_(ProjectTask.due_date < period_start, ProjectTask.stage.in_(['inbox', 'waiting', 'executing', 'pending', 'suspended'])),
            )
        )
        .all()
    )
    for task in tasks:
        project = task.project
        metadata = {
            'source_label': 'Atividade de projeto',
            'source_code': task.code,
            'project_id': task.project_id,
            'project_name': project.name if project else None,
            'project_code': project.code if project else None,
            'manual_assignment': current_manual_assignment(company_id, 'project_task', task.id),
            'source_url': f'/projects/{task.project_id}/manage' if task.project_id else None,
        }
        upsert_source_item(
            company_id=company_id,
            employee_id=employee_id,
            item_type='project_task',
            source_id=task.id,
            title=task.what,
            description=task.how,
            due_date=task.due_date,
            estimated_minutes=int(float(task.estimated_hours or 0) * 60),
            worked_minutes=int(float(task.worked_hours or 0) * 60),
            priority=str(task.priority or 'normal'),
            status=normalize_project_task_status(task.stage or task.status),
            recurrence_type='sporadic',
            metadata=metadata,
        )


def sync_meetings(company_id: int, employee_id: int, period_start: date, period_end: date) -> None:
    employee = ensure_employee(company_id, employee_id)
    meetings = (
        Meeting.query.filter_by(company_id=company_id)
        .filter(Meeting.scheduled_date.between(period_start, period_end))
        .all()
    )
    for meeting in meetings:
        if not meeting_matches_employee(meeting, employee) and not current_manual_assignment(company_id, 'meeting', meeting.id):
            continue
        metadata = {
            'source_label': 'Reunião',
            'source_code': f'{meeting.company.client_code if meeting.company and meeting.company.client_code else "AA"}.R.{meeting.id}',
            'project_id': meeting.project_id,
            'scheduled_time': meeting.scheduled_time,
            'planned_duration_minutes': int(meeting.planned_duration_minutes or 0),
            'manual_assignment': current_manual_assignment(company_id, 'meeting', meeting.id),
            'source_url': f'/meetings/company/{company_id}/meeting/{meeting.id}/report',
        }
        upsert_source_item(
            company_id=company_id,
            employee_id=employee_id,
            item_type='meeting',
            source_id=meeting.id,
            title=meeting.title,
            description=meeting.invite_notes or meeting.meeting_notes,
            due_date=meeting.scheduled_date,
            estimated_minutes=int(meeting.planned_duration_minutes or 60),
            worked_minutes=int(meeting.actual_duration_minutes or 0),
            priority='normal',
            status='completed' if str(meeting.status or '').lower() in {'done', 'completed'} else 'pending',
            recurrence_type='sporadic',
            metadata=metadata,
        )


def upsert_source_item(**kwargs) -> None:
    company_id = kwargs['company_id']
    item_type = kwargs['item_type']
    source_id = kwargs['source_id']
    item = WorkJourneyItem.query.filter_by(company_id=company_id, item_type=item_type, source_id=source_id).first()
    if not item:
        item = WorkJourneyItem(company_id=company_id, item_type=item_type, source_id=source_id)
    manual_assignment = bool((item.metadata_json or {}).get('manual_assignment')) or bool(kwargs['metadata'].get('manual_assignment'))
    if not manual_assignment:
        item.employee_id = kwargs['employee_id']
    previous_binding_block_id = (item.metadata_json or {}).get('routine_binding_block_id')
    item.title = kwargs['title']
    item.description = kwargs['description']
    item.due_date = kwargs['due_date']
    item.estimated_minutes = max(int(kwargs['estimated_minutes'] or 0), 0)
    item.worked_minutes = max(int(kwargs['worked_minutes'] or 0), 0)
    item.priority = kwargs['priority'] if kwargs['priority'] in PRIORITY_ORDER else 'normal'
    item.status = kwargs['status']
    item.recurrence_type = kwargs['recurrence_type']
    item.metadata_json = dict(kwargs['metadata'] or {})
    bound_block_id = kwargs.get('bound_block_id')
    if not manual_assignment:
        if item.block_id is None or item.block_id == previous_binding_block_id:
            item.block_id = bound_block_id
    if bound_block_id:
        item.metadata_json['routine_binding_block_id'] = bound_block_id
    else:
        item.metadata_json.pop('routine_binding_block_id', None)
    if manual_assignment:
        item.metadata_json['manual_assignment'] = True
    item.last_synced_at = datetime.utcnow()
    db.session.add(item)


def current_manual_assignment(company_id: int, item_type: str, source_id: int) -> bool:
    item = WorkJourneyItem.query.filter_by(company_id=company_id, item_type=item_type, source_id=source_id).first()
    return bool(item and (item.metadata_json or {}).get('manual_assignment'))


def meeting_matches_employee(meeting: Meeting, employee: Employee) -> bool:
    payloads = []
    for raw in (meeting.participants_json, meeting.guests_json):
        if not raw:
            continue
        try:
            loaded = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            loaded = []
        if isinstance(loaded, list):
            payloads.extend(loaded)
    employee_email = str(employee.email or '').strip().lower()
    employee_name = str(employee.name or '').strip().lower()
    for item in payloads:
        name = str(item.get('name') or '').strip().lower() if isinstance(item, dict) else ''
        email = str(item.get('email') or '').strip().lower() if isinstance(item, dict) else ''
        if employee_email and email == employee_email:
            return True
        if employee_name and name == employee_name:
            return True
    return False


def normalize_source_status(status: str | None) -> str:
    normalized = str(status or 'pending').strip().lower()
    if normalized in {'completed', 'done'}:
        return 'completed'
    if normalized in {'in_progress', 'executing'}:
        return 'in_progress'
    if normalized in {'suspended'}:
        return 'suspended'
    if normalized in {'postponed', 'waiting'}:
        return 'postponed'
    return 'pending'


def normalize_project_task_status(stage: str | None) -> str:
    normalized = str(stage or 'pending').strip().lower()
    if normalized == 'completed':
        return 'completed'
    if normalized in {'executing', 'in_progress'}:
        return 'in_progress'
    if normalized == 'suspended':
        return 'suspended'
    if normalized == 'waiting':
        return 'postponed'
    return 'pending'


def propagate_item_status(item: WorkJourneyItem) -> None:
    if item.item_type == 'project_task' and item.source_id:
        task = ProjectTask.query.get(item.source_id)
        if not task:
            return
        mapping = {
            'completed': ('completed', 'completed'),
            'in_progress': ('in_progress', 'executing'),
            'postponed': ('planned', 'waiting'),
            'suspended': ('planned', 'suspended'),
            'pending': ('planned', 'pending'),
        }
        task.status, task.stage = mapping.get(item.status, ('planned', 'pending'))
        task.worked_hours = round((item.worked_minutes or 0) / 60, 2)
        task.completion_date = date.today() if item.status == 'completed' else None
        if task.employee and not task.who:
            task.who = task.employee.name
        db.session.add(task)
        return

    if item.item_type == 'process_instance' and item.source_id:
        instance = ProcessInstance.query.get(item.source_id)
        if not instance:
            return
        mapping = {
            'completed': 'completed',
            'in_progress': 'in_progress',
            'pending': 'pending',
            'postponed': 'pending',
            'suspended': 'pending',
        }
        instance.status = mapping.get(item.status, 'pending')
        instance.actual_hours = round((item.worked_minutes or 0) / 60, 2)
        instance.worked_hours = round((item.worked_minutes or 0) / 60, 2)
        instance.completed_at = datetime.utcnow() if item.status == 'completed' else None
        db.session.add(instance)
        return

    if item.item_type == 'meeting' and item.source_id:
        meeting = Meeting.query.get(item.source_id)
        if not meeting:
            return
        meeting.status = 'done' if item.status == 'completed' else 'scheduled'
        meeting.actual_duration_minutes = item.worked_minutes or meeting.actual_duration_minutes
        db.session.add(meeting)
