from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models import (
    db,
    Employee,
    ProcessInstance,
    ProjectTask,
    WorkJourneyAbsenceRequest,
    WorkJourneyItem,
    WorkJourneyTransferRequest,
)
from services.work_journey_base import WorkJourneyError, ensure_employee
from services.work_journey_service import sync_work_journey_items


def list_absence_requests(company_id: int, employee_id: int | None = None) -> list[dict[str, Any]]:
    query = WorkJourneyAbsenceRequest.query.filter_by(company_id=company_id)
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    requests = query.order_by(WorkJourneyAbsenceRequest.created_at.desc()).all()
    return [serialize_absence_request(item) for item in requests]


def create_absence_request(company_id: int, payload: dict[str, Any], user_id: int | None) -> dict[str, Any]:
    employee = ensure_employee(company_id, payload['employee_id'])
    request = WorkJourneyAbsenceRequest(
        company_id=company_id,
        employee_id=employee.id,
        requested_by_user_id=user_id,
        absence_type=payload['absence_type'],
        start_date=payload['start_date'],
        end_date=payload['end_date'],
        reason=payload.get('reason'),
        metadata_json={},
    )
    db.session.add(request)
    db.session.commit()
    return serialize_absence_request(request)


def approve_absence_request(company_id: int, request_id: int, approver_user_id: int | None, cleanup_notes: str | None = None) -> dict[str, Any]:
    request = WorkJourneyAbsenceRequest.query.filter_by(company_id=company_id, id=request_id).first()
    if not request:
        raise WorkJourneyError('Solicitação de ausência não encontrada.')

    sync_work_journey_items(company_id, request.employee_id, request.start_date, request.end_date)
    pending_items = _active_items_in_period(company_id, request.employee_id, request.start_date, request.end_date)
    unresolved = [item for item in pending_items if item.status not in {'completed', 'suspended'}]
    if unresolved:
        raise WorkJourneyError('Ainda existem atividades ativas no período. Realoque ou suspenda antes de aprovar a ausência.')

    request.status = 'approved'
    request.cleanup_notes = cleanup_notes
    request.approved_by_user_id = approver_user_id
    request.approved_at = datetime.utcnow()

    db.session.add(request)
    db.session.commit()
    return serialize_absence_request(request)


def serialize_absence_request(request: WorkJourneyAbsenceRequest) -> dict[str, Any]:
    payload = request.to_dict()
    payload['impacted_items'] = [item.to_dict() for item in _active_items_in_period(request.company_id, request.employee_id, request.start_date, request.end_date)]
    return payload


def create_transfer_request(company_id: int, item_id: int, to_employee_id: int, reason: str | None, user_id: int | None) -> dict[str, Any]:
    item = WorkJourneyItem.query.filter_by(company_id=company_id, id=item_id).first()
    if not item:
        raise WorkJourneyError('Atividade não encontrada para transferência.')
    if item.employee_id == to_employee_id:
        raise WorkJourneyError('Selecione outro colaborador para realizar a transferência.')
    ensure_employee(company_id, to_employee_id)
    transfer = WorkJourneyTransferRequest(
        company_id=company_id,
        item_id=item.id,
        from_employee_id=item.employee_id,
        to_employee_id=to_employee_id,
        requested_by_user_id=user_id,
        reason=reason,
    )
    db.session.add(transfer)
    db.session.commit()
    return transfer.to_dict()


def list_transfer_requests(company_id: int, employee_id: int | None = None) -> list[dict[str, Any]]:
    query = WorkJourneyTransferRequest.query.filter_by(company_id=company_id)
    if employee_id:
        query = query.filter(
            (WorkJourneyTransferRequest.from_employee_id == employee_id)
            | (WorkJourneyTransferRequest.to_employee_id == employee_id)
        )
    rows = query.order_by(WorkJourneyTransferRequest.created_at.desc()).all()
    return [serialize_transfer_request(row) for row in rows]


def approve_transfer_request(company_id: int, request_id: int, approver_user_id: int | None, resolution_notes: str | None = None) -> dict[str, Any]:
    transfer = WorkJourneyTransferRequest.query.filter_by(company_id=company_id, id=request_id).first()
    if not transfer:
        raise WorkJourneyError('Solicitação de transferência não encontrada.')

    item = WorkJourneyItem.query.filter_by(company_id=company_id, id=transfer.item_id).first()
    if not item:
        raise WorkJourneyError('Atividade de transferência não encontrada.')

    item.employee_id = transfer.to_employee_id
    metadata = dict(item.metadata_json or {})
    metadata['manual_assignment'] = True
    metadata['transfer_request_id'] = transfer.id
    item.metadata_json = metadata

    if item.item_type == 'project_task' and item.source_id:
        task = ProjectTask.query.get(item.source_id)
        if task:
            employee = Employee.query.filter_by(company_id=company_id, id=transfer.to_employee_id).first()
            task.employee_id = transfer.to_employee_id
            task.who = employee.name if employee else task.who
            db.session.add(task)
    elif item.item_type == 'process_instance' and item.source_id:
        instance = ProcessInstance.query.get(item.source_id)
        if instance:
            instance.executor_id = transfer.to_employee_id
            db.session.add(instance)

    transfer.status = 'approved'
    transfer.approved_by_user_id = approver_user_id
    transfer.approved_at = datetime.utcnow()
    transfer.resolution_notes = resolution_notes
    db.session.add(item)
    db.session.add(transfer)
    db.session.commit()
    return serialize_transfer_request(transfer)


def serialize_transfer_request(request: WorkJourneyTransferRequest) -> dict[str, Any]:
    payload = request.to_dict()
    payload['item'] = request.item.to_dict() if request.item else None
    payload['from_employee_name'] = request.from_employee.name if request.from_employee else None
    payload['to_employee_name'] = request.to_employee.name if request.to_employee else None
    return payload


def _active_items_in_period(company_id: int, employee_id: int, start_date: date, end_date: date) -> list[WorkJourneyItem]:
    return (
        WorkJourneyItem.query.filter(
            WorkJourneyItem.company_id == company_id,
            WorkJourneyItem.employee_id == employee_id,
            WorkJourneyItem.status != 'completed',
            WorkJourneyItem.due_date.between(start_date, end_date),
        )
        .order_by(WorkJourneyItem.due_date.asc(), WorkJourneyItem.id.asc())
        .all()
    )
