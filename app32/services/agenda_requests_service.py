"""Ausencias e transferencias na Agenda (Fase 5): leitura com escopo e contagem de pendencias.

Privacidade: quem NAO e gestor ve somente as proprias ausencias e as transferencias em que e origem ou destino.
O motivo de uma ausencia (ex.: atestado) nunca sai para quem nao e o proprio colaborador ou gestor.
A aprovacao continua nas rotas existentes (somente gestor/administrador).
"""

from __future__ import annotations

from typing import Any

from models import Employee, WorkJourneyAbsenceRequest, WorkJourneyItem, WorkJourneyTransferRequest

ABSENCE_LABELS = {"vacation": "Férias", "absence": "Ausência", "medical_leave": "Atestado médico"}
STATUS_LABELS = {"pending": "Pendente", "approved": "Aprovada", "rejected": "Recusada", "cancelled": "Cancelada"}
LIST_LIMIT = 100


def _names(ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {e.id: e.name for e in Employee.query.filter(Employee.id.in_(ids)).all()}


def list_requests(company_id: int, *, viewer_employee_id: int | None, is_manager: bool) -> dict[str, Any]:
    absences_q = WorkJourneyAbsenceRequest.query.filter_by(company_id=company_id)
    transfers_q = WorkJourneyTransferRequest.query.filter_by(company_id=company_id)
    if not is_manager:
        if not viewer_employee_id:
            return {"absences": [], "transfers": [], "pending_total": 0, "is_manager": False}
        absences_q = absences_q.filter(WorkJourneyAbsenceRequest.employee_id == viewer_employee_id)
        transfers_q = transfers_q.filter(
            (WorkJourneyTransferRequest.from_employee_id == viewer_employee_id)
            | (WorkJourneyTransferRequest.to_employee_id == viewer_employee_id)
        )
    absences = absences_q.order_by(WorkJourneyAbsenceRequest.created_at.desc()).limit(LIST_LIMIT).all()
    transfers = transfers_q.order_by(WorkJourneyTransferRequest.created_at.desc()).limit(LIST_LIMIT).all()

    names = _names(
        {a.employee_id for a in absences} | {t.from_employee_id for t in transfers} | {t.to_employee_id for t in transfers}
    )
    item_ids = {t.item_id for t in transfers if t.item_id}
    titles = (
        {i.id: i.title for i in WorkJourneyItem.query.filter(WorkJourneyItem.company_id == company_id, WorkJourneyItem.id.in_(item_ids)).all()}
        if item_ids
        else {}
    )

    out_absences = [
        {
            "id": a.id,
            "employee_id": a.employee_id,
            "employee_name": names.get(a.employee_id),
            "type": a.absence_type,
            "type_label": ABSENCE_LABELS.get(a.absence_type, a.absence_type),
            "start_date": a.start_date.isoformat() if a.start_date else None,
            "end_date": a.end_date.isoformat() if a.end_date else None,
            "reason": a.reason,
            "status": a.status,
            "status_label": STATUS_LABELS.get(a.status, a.status),
            "can_approve": bool(is_manager and a.status == "pending"),
        }
        for a in absences
    ]
    out_transfers = [
        {
            "id": t.id,
            "item_title": titles.get(t.item_id),
            "from_employee_id": t.from_employee_id,
            "from_name": names.get(t.from_employee_id),
            "to_employee_id": t.to_employee_id,
            "to_name": names.get(t.to_employee_id),
            "reason": t.reason,
            "status": t.status,
            "status_label": STATUS_LABELS.get(t.status, t.status),
            "can_approve": bool(is_manager and t.status == "pending"),
        }
        for t in transfers
    ]
    pending = sum(1 for a in out_absences if a["status"] == "pending") + sum(1 for t in out_transfers if t["status"] == "pending")
    return {
        "absences": out_absences,
        "transfers": out_transfers,
        "pending_total": pending if is_manager else 0,  # contador de aprovacoes so faz sentido para o gestor
        "is_manager": bool(is_manager),
    }
