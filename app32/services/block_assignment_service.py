"""Atribuir, mover e sugerir itens em blocos (Fase 2 da Agenda unificada).

Regras: docs/spec/agenda_unificada_blocos_pessoa_v1.md, secao 5.5.
- Atribuir/mover e sempre ato da pessoa; o sistema so SUGERE (marca `suggested_by`).
- Mesmo dia: nao altera o prazo. Atividade em outro dia: usa o fluxo existente de
  mudanca de prazo (motivo obrigatorio; pode virar solicitacao pendente).
- Instancia so se move entre blocos do mesmo dia.
- Nenhum sinal bloqueia a acao.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from models import (
    ProcessInstance,
    Project,
    ProjectTask,
    WorkJourneyAgendaItem,
    WorkJourneyBlock,
    WorkJourneyItem,
    db,
)
from services.agenda_block_view_service import build_block_view
from services.block_signal_service import OPERATIONAL_MODE, SIGNAL_OVER, signal_for
from services.work_journey_agenda_engine import build_entry, next_position_for_group, recompute_agenda_summary
from services.work_journey_agenda_service import _get_or_build_agenda, _resolve_target_block
from services.work_journey_base import WorkJourneyError

HORIZON_DAYS = 14
MAX_OPTIONS = 5
MOVABLE_TYPES = ("project_task", "process_instance")
SUGGESTED_BY = "system"


class AssignmentError(ValueError):
    pass


def rank_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cabem primeiro; depois as do mesmo dia; depois a data mais proxima e o horario."""
    return sorted(options, key=lambda o: (not o["fits"], not o["same_day"], o["date"], o["start_minutes"]))


def _journey_item(company_id: int, employee_id: int, source_type: str, source_id: int) -> WorkJourneyItem:
    if source_type not in MOVABLE_TYPES:
        raise AssignmentError("Só atividades e instâncias podem ser movidas para um bloco.")
    item = WorkJourneyItem.query.filter_by(
        company_id=company_id, employee_id=employee_id, item_type=source_type, source_id=source_id
    ).first()
    if item is None:
        raise AssignmentError("Item não encontrado na jornada deste colaborador.")
    return item


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _due_date(item: WorkJourneyItem) -> date | None:
    return item.due_date or item.occurrence_date


def move_options(
    company_id: int,
    employee_id: int,
    source_type: str,
    source_id: int,
    *,
    today: date | None = None,
    limit: int = MAX_OPTIONS,
) -> dict[str, Any]:
    """Ate `limit` destinos possiveis, com o estado atual do bloco e o que ficaria."""
    item = _journey_item(company_id, employee_id, source_type, source_id)
    today = today or date.today()
    due = _due_date(item)
    estimate = int(item.estimated_minutes or 0)
    end = today + timedelta(days=HORIZON_DAYS - 1)

    blocks = {
        b.id: b
        for b in WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True).all()
    }
    view = build_block_view(company_id, employee_id, today, end)
    current = (
        WorkJourneyAgendaItem.query.filter(
            WorkJourneyAgendaItem.company_id == company_id,
            WorkJourneyAgendaItem.employee_id == employee_id,
            WorkJourneyAgendaItem.journey_item_id == item.id,
            WorkJourneyAgendaItem.block_id.isnot(None),
        )
        .all()
    )
    already = {(e.planned_date, e.block_id) for e in current}

    options: list[dict[str, Any]] = []
    for day in view["days"]:
        day_date = date.fromisoformat(day["date"])
        changes_due = due is not None and day_date != due
        if changes_due and source_type == "process_instance":
            continue  # instâncias só se movem dentro do mesmo dia (SPEC RF-MOV-3)
        for entry in day["blocks"]:
            block = blocks.get(entry["id"])
            if block is None or entry["mode"] != OPERATIONAL_MODE:
                continue
            if source_type not in (block.accepted_item_types or []):
                continue
            if (day_date, entry["id"]) in already:
                continue
            before = entry["signal"]
            after = signal_for(entry["capacity_minutes"], entry["consumed_minutes"] + estimate, view["idle_threshold"]) if estimate > 0 else before
            options.append(
                {
                    "date": day["date"],
                    "block_id": entry["id"],
                    "block_name": entry["name"],
                    "start": entry["start"],
                    "end": entry["end"],
                    "start_minutes": entry["start_minutes"],
                    "before": {"state": before["state"], "label": before["label"]},
                    "after": {"state": after["state"], "label": after["label"]},
                    "fits": after["state"] != SIGNAL_OVER,
                    "same_day": not changes_due,
                    "changes_due_date": changes_due,
                    "needs_reason": changes_due and source_type == "project_task",
                }
            )
    ranked = rank_options(options)[: max(1, int(limit))]
    for option in ranked:
        option.pop("start_minutes", None)
    return {
        "item": {"type": source_type, "id": source_id, "title": item.title, "estimated_minutes": estimate, "without_estimate": estimate <= 0},
        "options": ranked,
    }


def _ensure_entry(company_id: int, employee_id: int, item: WorkJourneyItem, target_date: date, block: WorkJourneyBlock):
    agenda = _get_or_build_agenda(company_id, employee_id, target_date, "day", False)
    if agenda.status == "locked":
        raise AssignmentError("A agenda deste dia está travada. Destrave para mover itens.")
    entry = WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda.id, journey_item_id=item.id, planned_date=target_date).first()
    if entry is None:
        entry = build_entry(
            agenda, item, planned_date=target_date, block=block, allocated_minutes=int(item.estimated_minutes or 0),
            position_index=next_position_for_group(agenda.id, target_date, block.id), is_fixed=False,
            is_over_capacity=False, overflow_minutes=0,
        )
        db.session.add(entry)
        db.session.flush()
    return agenda, entry


def _place(company_id, employee_id, item, target_date, block_id, *, suggested: bool) -> WorkJourneyAgendaItem:
    try:
        block = _resolve_target_block(company_id, employee_id, target_date, item.item_type, block_id)
    except WorkJourneyError as exc:
        raise AssignmentError(str(exc))
    if block is None:
        raise AssignmentError("Informe o bloco de destino.")
    agenda, entry = _ensure_entry(company_id, employee_id, item, target_date, block)
    entry.block_id = block.id
    entry.planned_date = target_date
    entry.allocated_minutes = int(item.estimated_minutes or 0)
    entry.position_index = next_position_for_group(agenda.id, target_date, block.id)
    entry.manual_override = True  # sobrevive à regeneração da agenda
    metadata = dict(entry.metadata_json or {})
    metadata.pop("unassigned_reason", None)
    if suggested:
        metadata["suggested_by"] = SUGGESTED_BY
    else:
        metadata.pop("suggested_by", None)  # o que a pessoa atribui nunca é "sugestão"
    entry.metadata_json = metadata
    entry.updated_at = datetime.utcnow()
    db.session.add(entry)
    db.session.flush()
    recompute_agenda_summary(agenda)
    return entry


def assign_item(
    company_id: int,
    employee_id: int,
    source_type: str,
    source_id: int,
    target_date: date,
    block_id: int,
    *,
    reason: str | None = None,
    suggested: bool = False,
) -> dict[str, Any]:
    """Atribui o item a um bloco/dia. Atividade em outro dia passa pelo fluxo de mudança de prazo."""
    item = _journey_item(company_id, employee_id, source_type, source_id)
    due = _due_date(item)
    status = "assigned"
    message = None

    if due is not None and target_date != due:
        if source_type != "project_task":
            raise AssignmentError("Instâncias só podem ser movidas entre blocos do mesmo dia.")
        if not str(reason or "").strip():
            raise AssignmentError("Informe o motivo da mudança de prazo.")
        task = ProjectTask.query.get(source_id)
        project = Project.query.filter_by(id=task.project_id, company_id=company_id).first() if task else None
        if task is None or project is None:
            raise AssignmentError("Atividade não encontrada.")
        from services.project_task_due_date_change_service import ProjectTaskDueDateChangeService

        request_obj, _task, applied, error = ProjectTaskDueDateChangeService.create_or_apply_request(
            company_id=company_id, project_id=project.id, task_id=task.id, requested_due_date=target_date, reason=str(reason).strip(),
        )
        if error:
            raise AssignmentError(str(error))
        if not applied:
            db.session.commit()
            return {"status": "pending", "message": "Pedido de mudança de prazo enviado para aprovação. O item continua onde está até a decisão."}
        item.due_date = target_date
        item.occurrence_date = target_date
        db.session.add(item)
        message = "Prazo atualizado e item movido."

    _place(company_id, employee_id, item, target_date, block_id, suggested=suggested)
    db.session.commit()
    return {"status": status, "message": message or "Item movido para o bloco."}


def suggest_distribution(company_id: int, employee_id: int, target_date: date) -> dict[str, Any]:
    """Propõe blocos para os itens do dia ainda sem bloco, respeitando capacidade e tipos aceitos.

    Não grava nada. Itens que não cabem ficam "sem bloco", nunca forçados (RF-MOV-1).
    """
    placed_ids = {
        e.journey_item_id
        for e in WorkJourneyAgendaItem.query.filter(
            WorkJourneyAgendaItem.company_id == company_id,
            WorkJourneyAgendaItem.employee_id == employee_id,
            WorkJourneyAgendaItem.planned_date == target_date,
            WorkJourneyAgendaItem.block_id.isnot(None),
        ).all()
    }
    pending = [
        i
        for i in WorkJourneyItem.query.filter(
            WorkJourneyItem.company_id == company_id,
            WorkJourneyItem.employee_id == employee_id,
            WorkJourneyItem.item_type.in_(MOVABLE_TYPES),
            WorkJourneyItem.due_date == target_date,
            WorkJourneyItem.status.notin_(["completed", "done", "cancelled", "postponed", "suspended"]),
        ).all()
        if i.id not in placed_ids and int(i.estimated_minutes or 0) > 0
    ]
    pending.sort(key=lambda i: (-int(i.estimated_minutes or 0), i.id))

    view = build_block_view(company_id, employee_id, target_date, target_date)
    day = view["days"][0] if view["days"] else {"blocks": []}
    blocks = {b.id: b for b in WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True).all()}
    free = {b["id"]: b["capacity_minutes"] - b["consumed_minutes"] for b in day["blocks"] if b["mode"] == OPERATIONAL_MODE}
    order = [b["id"] for b in day["blocks"] if b["mode"] == OPERATIONAL_MODE]
    names = {b["id"]: b["name"] for b in day["blocks"]}

    proposals: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []
    for item in pending:
        need = int(item.estimated_minutes)
        target = next(
            (bid for bid in order if free[bid] >= need and item.item_type in (blocks[bid].accepted_item_types or [])), None
        )
        if target is None:
            unplaced.append({"type": item.item_type, "id": item.source_id, "title": item.title, "minutes": need})
            continue
        free[target] -= need
        proposals.append(
            {"type": item.item_type, "id": item.source_id, "title": item.title, "minutes": need, "block_id": target, "block_name": names[target]}
        )
    return {"date": target_date.isoformat(), "proposals": proposals, "unplaced": unplaced}


def apply_suggestions(company_id: int, employee_id: int, target_date: date) -> dict[str, Any]:
    """Aplica a sugestão marcando cada item como `suggested_by=system` (a pessoa aceita ou desfaz)."""
    plan = suggest_distribution(company_id, employee_id, target_date)
    applied = 0
    for proposal in plan["proposals"]:
        item = _journey_item(company_id, employee_id, proposal["type"], proposal["id"])
        _place(company_id, employee_id, item, target_date, proposal["block_id"], suggested=True)
        applied += 1
    db.session.commit()
    return {"applied": applied, "unplaced": plan["unplaced"]}


def _suggested_entries(company_id: int, employee_id: int, target_date: date) -> list[WorkJourneyAgendaItem]:
    rows = WorkJourneyAgendaItem.query.filter(
        WorkJourneyAgendaItem.company_id == company_id,
        WorkJourneyAgendaItem.employee_id == employee_id,
        WorkJourneyAgendaItem.planned_date == target_date,
    ).all()
    return [e for e in rows if (e.metadata_json or {}).get("suggested_by") == SUGGESTED_BY]


def undo_suggestions(company_id: int, employee_id: int, target_date: date) -> dict[str, int]:
    """Remove só o que o sistema sugeriu; o que a pessoa atribuiu nunca é tocado (RF-MOV-5)."""
    removed = 0
    for entry in _suggested_entries(company_id, employee_id, target_date):
        agenda = entry.agenda
        if agenda is not None and agenda.status == "locked":
            continue
        db.session.delete(entry)
        removed += 1
    db.session.commit()
    return {"removed": removed}


def accept_suggestions(company_id: int, employee_id: int, target_date: date) -> dict[str, int]:
    """A pessoa aceita a sugestão: vira atribuição dela (perde a marca de sugerido)."""
    accepted = 0
    for entry in _suggested_entries(company_id, employee_id, target_date):
        metadata = dict(entry.metadata_json or {})
        metadata.pop("suggested_by", None)
        entry.metadata_json = metadata
        db.session.add(entry)
        accepted += 1
    db.session.commit()
    return {"accepted": accepted}
