"""Adaptador de blocos efetivos (SPEC agenda unificada, secao 6.4).

`get_effective_blocks(company_id, employee_id)`:
1. se o colaborador tem `user_id` e esse usuario tem ao menos um bloco da pessoa ativo,
   devolve os blocos da PESSOA (um dia unico, valendo para todas as empresas);
2. caso contrario, devolve os blocos legados da empresa (comportamento de hoje).

Nao ha chave global: o usuario so "vira" pessoa depois de migrar.
"""

from __future__ import annotations

from typing import Any

from models import Employee, PersonWorkBlock, WorkJourneyBlock

SOURCE_PERSON = "person"
SOURCE_LEGACY = "legacy"


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _minutes(value) -> int:
    return value.hour * 60 + value.minute


def person_block_def(block: PersonWorkBlock) -> dict[str, Any]:
    start, end = _minutes(block.start_time), _minutes(block.end_time)
    return {
        "id": block.id,
        "source": SOURCE_PERSON,
        "name": block.name,
        "mode": block.block_mode or "operational",
        "start_minutes": start,
        "end_minutes": end,
        "start": _hhmm(start),
        "end": _hhmm(end),
        "weekdays": list(block.weekdays_json or []),
        "preferred_types": list(block.preferred_item_types or []),
        "accepted_types": None,  # o bloco da pessoa aceita qualquer item (RF-BLO-4)
        "order_index": int(block.order_index or 0),
    }


def legacy_block_def(block: WorkJourneyBlock) -> dict[str, Any]:
    start, end = _minutes(block.start_time), _minutes(block.end_time)
    return {
        "id": block.id,
        "source": SOURCE_LEGACY,
        "name": block.name,
        "mode": block.block_mode or "operational",
        "start_minutes": start,
        "end_minutes": end,
        "start": _hhmm(start),
        "end": _hhmm(end),
        "weekdays": list(block.weekdays_json or []),
        "preferred_types": [],
        "accepted_types": list(block.accepted_item_types or []),
        "order_index": int(block.order_index or 0),
    }


def user_has_person_blocks(user_id: int | None) -> bool:
    if not user_id:
        return False
    return PersonWorkBlock.query.filter_by(user_id=user_id, is_active=True).first() is not None


def person_blocks(user_id: int) -> list[dict[str, Any]]:
    rows = (
        PersonWorkBlock.query.filter_by(user_id=user_id, is_active=True)
        .order_by(PersonWorkBlock.start_time, PersonWorkBlock.order_index, PersonWorkBlock.id)
        .all()
    )
    return [person_block_def(b) for b in rows]


def legacy_blocks(company_id: int, employee_id: int) -> list[dict[str, Any]]:
    rows = (
        WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True)
        .order_by(WorkJourneyBlock.start_time, WorkJourneyBlock.order_index)
        .all()
    )
    return [legacy_block_def(b) for b in rows]


def get_effective_blocks(company_id: int, employee_id: int) -> dict[str, Any]:
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if employee is not None and user_has_person_blocks(employee.user_id):
        return {"source": SOURCE_PERSON, "user_id": employee.user_id, "blocks": person_blocks(employee.user_id)}
    return {"source": SOURCE_LEGACY, "user_id": employee.user_id if employee is not None else None, "blocks": legacy_blocks(company_id, employee_id)}
