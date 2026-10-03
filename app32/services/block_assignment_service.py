"""Atribuir, mover e sugerir itens em blocos (Fases 2 e 3 da Agenda unificada).

Regras: docs/spec/agenda_unificada_blocos_pessoa_v1.md, secao 5.5.
- Atribuir/mover e sempre ato da pessoa; o sistema so SUGERE (marca `suggested_by`).
- Mesmo dia: nao altera o prazo. Atividade em outro dia: usa o fluxo existente de
  mudanca de prazo (motivo obrigatorio; pode virar solicitacao pendente).
- Instancia so se move entre blocos do mesmo dia.
- Nenhum sinal bloqueia a acao.

Dois modos (adaptador de blocos efetivos): blocos legados da empresa (grava `block_id`) ou
blocos da pessoa (grava `person_block_id`). O modo pessoa so vale quando o proprio dono
do colaborador opera a propria agenda (`viewer_user_id`).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from models import (
    Employee,
    PersonWorkBlock,
    ProjectTask,
    Project,
    WorkJourneyAgendaItem,
    WorkJourneyItem,
    db,
)
from services.agenda_block_view_service import build_block_view
from services.block_signal_service import OPERATIONAL_MODE, SIGNAL_OVER, signal_for
from services.effective_blocks_service import legacy_blocks, person_blocks, user_has_person_blocks
from services.work_journey_agenda_engine import build_entry, next_position_for_group, recompute_agenda_summary
from services.work_journey_agenda_service import _get_or_build_agenda, _resolve_target_block
from services.work_journey_base import WorkJourneyError

HORIZON_DAYS = 14
MAX_OPTIONS = 5
MOVABLE_TYPES = ("project_task", "process_instance")
SUGGESTED_BY = "system"
_CLOSED = ["completed", "done", "cancelled", "postponed", "suspended"]


class AssignmentError(ValueError):
    pass


def rank_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cabem primeiro; depois as do mesmo dia; depois a data mais proxima e o horario."""
    return sorted(options, key=lambda o: (not o["fits"], not o["same_day"], o["date"], o["start_minutes"]))


def _person_mode(company_id: int, employee_id: int, viewer_user_id: int | None) -> int | None:
    """Devolve o user_id quando vale o modo pessoa; senao None (modo legado)."""
    if viewer_user_id is None:
        return None
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if employee is not None and employee.user_id == viewer_user_id and user_has_person_blocks(viewer_user_id):
        return viewer_user_id
    return None


def _scope_employee_ids(company_id: int, employee_id: int, person_user: int | None, allowed: set[int] | None = None) -> set[int]:
    if person_user is None:
        return {employee_id}
    rows = Employee.query.filter(Employee.user_id == person_user, Employee.status == "active").all()
    return {e.id for e in rows if allowed is None or e.company_id in allowed or e.company_id == company_id} | {employee_id}


def _journey_item(company_id: int, employee_id: int, source_type: str, source_id: int) -> WorkJourneyItem:
    if source_type not in MOVABLE_TYPES:
        raise AssignmentError("Só atividades e instâncias podem ser movidas para um bloco.")
    item = WorkJourneyItem.query.filter_by(
        company_id=company_id, employee_id=employee_id, item_type=source_type, source_id=source_id
    ).first()
    if item is None:
        raise AssignmentError("Item não encontrado na jornada deste colaborador.")
    return item


def _due_date(item: WorkJourneyItem) -> date | None:
    return item.due_date or item.occurrence_date


def _block_accepts(block_def: dict[str, Any], item_type: str) -> bool:
    accepted = block_def.get("accepted_types")
    return True if accepted is None else item_type in accepted  # bloco da pessoa aceita qualquer item


def move_options(
    company_id: int,
    employee_id: int,
    source_type: str,
    source_id: int,
    *,
    today: date | None = None,
    limit: int = MAX_OPTIONS,
    viewer_user_id: int | None = None,
    allowed_company_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Ate `limit` destinos possiveis, com o estado atual do bloco e o que ficaria."""
    item = _journey_item(company_id, employee_id, source_type, source_id)
    person_user = _person_mode(company_id, employee_id, viewer_user_id)
    today = today or date.today()
    due = _due_date(item)
    estimate = int(item.estimated_minutes or 0)
    end = today + timedelta(days=HORIZON_DAYS - 1)

    defs = {b["id"]: b for b in (person_blocks(person_user) if person_user else legacy_blocks(company_id, employee_id))}
    view = build_block_view(company_id, employee_id, today, end, viewer_user_id=viewer_user_id, allowed_company_ids=allowed_company_ids)
    column = WorkJourneyAgendaItem.person_block_id if person_user else WorkJourneyAgendaItem.block_id
    current = WorkJourneyAgendaItem.query.filter(
        WorkJourneyAgendaItem.company_id == company_id,
        WorkJourneyAgendaItem.employee_id == employee_id,
        WorkJourneyAgendaItem.journey_item_id == item.id,
        column.isnot(None),
    ).all()
    already = {(e.planned_date, e.person_block_id if person_user else e.block_id) for e in current}

    options: list[dict[str, Any]] = []
    for day in view["days"]:
        day_date = date.fromisoformat(day["date"])
        changes_due = due is not None and day_date != due
        if changes_due and source_type == "process_instance":
            continue  # instâncias só se movem dentro do mesmo dia (SPEC RF-MOV-3)
        for entry in day["blocks"]:
            block = defs.get(entry["id"])
            if block is None or entry["mode"] != OPERATIONAL_MODE:
                continue
            if not _block_accepts(block, source_type):
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
                    "preferred": source_type in (block.get("preferred_types") or []),
                }
            )
    ranked = rank_options(options)[: max(1, int(limit))]
    for option in ranked:
        option.pop("start_minutes", None)
    return {
        "source": view.get("source"),
        "item": {"type": source_type, "id": source_id, "title": item.title, "estimated_minutes": estimate, "without_estimate": estimate <= 0},
        "options": ranked,
    }


def _ensure_entry(company_id: int, employee_id: int, item: WorkJourneyItem, target_date: date):
    agenda = _get_or_build_agenda(company_id, employee_id, target_date, "day", False)
    if agenda.status == "locked":
        raise AssignmentError("A agenda deste dia está travada. Destrave para mover itens.")
    entry = WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda.id, journey_item_id=item.id, planned_date=target_date).first()
    if entry is None:
        entry = build_entry(
            agenda, item, planned_date=target_date, block=None, allocated_minutes=int(item.estimated_minutes or 0),
            position_index=0, is_fixed=False, is_over_capacity=False, overflow_minutes=0,
        )
        db.session.add(entry)
        db.session.flush()
    return agenda, entry


def _resolve_person_block(user_id: int, target_date: date, block_id: int | None) -> PersonWorkBlock:
    block = PersonWorkBlock.query.filter_by(id=block_id, user_id=user_id, is_active=True).first() if block_id else None
    if block is None:
        raise AssignmentError("Bloco de destino inválido.")
    if block.block_mode == "reserved_full":
        raise AssignmentError("Blocos com capacidade ocupada não aceitam tarefas.")
    if target_date.weekday() not in (block.weekdays_json or []):
        raise AssignmentError("O bloco informado não está ativo para o dia selecionado.")
    return block


def _place(company_id, employee_id, item, target_date, block_id, *, suggested: bool, person_user: int | None) -> WorkJourneyAgendaItem:
    if person_user is not None:
        legacy_id, person_id = None, _resolve_person_block(person_user, target_date, block_id).id
    else:
        try:
            block = _resolve_target_block(company_id, employee_id, target_date, item.item_type, block_id)
        except WorkJourneyError as exc:
            raise AssignmentError(str(exc))
        if block is None:
            raise AssignmentError("Informe o bloco de destino.")
        legacy_id, person_id = block.id, None
    agenda, entry = _ensure_entry(company_id, employee_id, item, target_date)
    entry.block_id = legacy_id
    entry.person_block_id = person_id
    entry.planned_date = target_date
    entry.allocated_minutes = int(item.estimated_minutes or 0)
    entry.position_index = next_position_for_group(agenda.id, target_date, legacy_id)
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
    viewer_user_id: int | None = None,
) -> dict[str, Any]:
    """Atribui o item a um bloco/dia. Atividade em outro dia passa pelo fluxo de mudança de prazo."""
    item = _journey_item(company_id, employee_id, source_type, source_id)
    person_user = _person_mode(company_id, employee_id, viewer_user_id)
    due = _due_date(item)
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

    _place(company_id, employee_id, item, target_date, block_id, suggested=suggested, person_user=person_user)
    db.session.commit()
    return {"status": "assigned", "message": message or "Item movido para o bloco."}


def _plan(company_id: int, employee_id: int, target_date: date, viewer_user_id: int | None, allowed: set[int] | None = None) -> dict[str, Any]:
    person_user = _person_mode(company_id, employee_id, viewer_user_id)
    scope_ids = _scope_employee_ids(company_id, employee_id, person_user, allowed)
    column = WorkJourneyAgendaItem.person_block_id if person_user else WorkJourneyAgendaItem.block_id
    placed = {
        e.journey_item_id
        for e in WorkJourneyAgendaItem.query.filter(
            WorkJourneyAgendaItem.employee_id.in_(scope_ids),
            WorkJourneyAgendaItem.planned_date == target_date,
            column.isnot(None),
        ).all()
    }
    query = WorkJourneyItem.query.filter(
        WorkJourneyItem.employee_id.in_(scope_ids),
        WorkJourneyItem.item_type.in_(MOVABLE_TYPES),
        WorkJourneyItem.due_date == target_date,
        WorkJourneyItem.status.notin_(_CLOSED),
    )
    if person_user is None:
        query = query.filter(WorkJourneyItem.company_id == company_id)
    pending = [i for i in query.all() if i.id not in placed and int(i.estimated_minutes or 0) > 0]
    pending.sort(key=lambda i: (-int(i.estimated_minutes or 0), i.id))

    view = build_block_view(company_id, employee_id, target_date, target_date, viewer_user_id=viewer_user_id, allowed_company_ids=allowed)
    day = view["days"][0] if view["days"] else {"blocks": []}
    defs = {b["id"]: b for b in (person_blocks(person_user) if person_user else legacy_blocks(company_id, employee_id))}
    operational = [b for b in day["blocks"] if b["mode"] == OPERATIONAL_MODE and b["id"] in defs]
    free = {b["id"]: b["capacity_minutes"] - b["consumed_minutes"] for b in operational}
    names = {b["id"]: b["name"] for b in operational}

    proposals: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []
    for item in pending:
        need = int(item.estimated_minutes)
        candidates = [b["id"] for b in operational if free[b["id"]] >= need and _block_accepts(defs[b["id"]], item.item_type)]
        # Blocos que preferem o tipo do item vêm primeiro; os demais continuam aceitos (RF-BLO-4).
        candidates.sort(key=lambda bid: item.item_type not in (defs[bid].get("preferred_types") or []))
        if not candidates:
            unplaced.append({"type": item.item_type, "id": item.source_id, "title": item.title, "minutes": need})
            continue
        target = candidates[0]
        free[target] -= need
        proposals.append(
            {
                "type": item.item_type, "id": item.source_id, "title": item.title, "minutes": need,
                "block_id": target, "block_name": names[target],
                "_company_id": item.company_id, "_employee_id": item.employee_id,
            }
        )
    return {"date": target_date.isoformat(), "proposals": proposals, "unplaced": unplaced, "_person_user": person_user}


def suggest_distribution(company_id: int, employee_id: int, target_date: date, *, viewer_user_id: int | None = None, allowed_company_ids: set[int] | None = None) -> dict[str, Any]:
    """Propõe blocos para os itens do dia ainda sem bloco, respeitando capacidade.

    Não grava nada. Itens que não cabem ficam "sem bloco", nunca forçados (RF-MOV-1).
    """
    plan = _plan(company_id, employee_id, target_date, viewer_user_id, allowed_company_ids)
    clean = [{k: v for k, v in p.items() if not k.startswith("_")} for p in plan["proposals"]]
    return {"date": plan["date"], "proposals": clean, "unplaced": plan["unplaced"]}


def apply_suggestions(company_id: int, employee_id: int, target_date: date, *, viewer_user_id: int | None = None, allowed_company_ids: set[int] | None = None) -> dict[str, Any]:
    """Aplica a sugestão marcando cada item como `suggested_by=system` (a pessoa aceita ou desfaz)."""
    plan = _plan(company_id, employee_id, target_date, viewer_user_id, allowed_company_ids)
    applied = 0
    for proposal in plan["proposals"]:
        item = _journey_item(proposal["_company_id"], proposal["_employee_id"], proposal["type"], proposal["id"])
        _place(proposal["_company_id"], proposal["_employee_id"], item, target_date, proposal["block_id"],
               suggested=True, person_user=plan["_person_user"])
        applied += 1
    db.session.commit()
    return {"applied": applied, "unplaced": plan["unplaced"]}


def _suggested_entries(company_id: int, employee_id: int, target_date: date, viewer_user_id: int | None, allowed: set[int] | None = None) -> list[WorkJourneyAgendaItem]:
    scope_ids = _scope_employee_ids(company_id, employee_id, _person_mode(company_id, employee_id, viewer_user_id), allowed)
    rows = WorkJourneyAgendaItem.query.filter(
        WorkJourneyAgendaItem.employee_id.in_(scope_ids),
        WorkJourneyAgendaItem.planned_date == target_date,
    ).all()
    return [e for e in rows if (e.metadata_json or {}).get("suggested_by") == SUGGESTED_BY]


def undo_suggestions(company_id: int, employee_id: int, target_date: date, *, viewer_user_id: int | None = None, allowed_company_ids: set[int] | None = None) -> dict[str, int]:
    """Remove só o que o sistema sugeriu; o que a pessoa atribuiu nunca é tocado (RF-MOV-5)."""
    removed = 0
    for entry in _suggested_entries(company_id, employee_id, target_date, viewer_user_id, allowed_company_ids):
        agenda = entry.agenda
        if agenda is not None and agenda.status == "locked":
            continue
        db.session.delete(entry)
        removed += 1
    db.session.commit()
    return {"removed": removed}


def accept_suggestions(company_id: int, employee_id: int, target_date: date, *, viewer_user_id: int | None = None, allowed_company_ids: set[int] | None = None) -> dict[str, int]:
    """A pessoa aceita a sugestão: vira atribuição dela (perde a marca de sugerido)."""
    accepted = 0
    for entry in _suggested_entries(company_id, employee_id, target_date, viewer_user_id, allowed_company_ids):
        metadata = dict(entry.metadata_json or {})
        metadata.pop("suggested_by", None)
        entry.metadata_json = metadata
        db.session.add(entry)
        accepted += 1
    db.session.commit()
    return {"accepted": accepted}
