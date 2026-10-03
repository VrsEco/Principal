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


# ---------------------------------------------------------------------------
# Consumidores legados (Calendario Operacional antigo, PDF, relatorios, incentivos)
# ---------------------------------------------------------------------------

ALL_ITEM_TYPES = ["manual", "process_instance", "project_task", "meeting"]


def person_mode_user(employee: Employee | None) -> int | None:
    """user_id do dono do colaborador quando ele migrou para blocos da pessoa; senao None (modo legado)."""
    user_id = getattr(employee, "user_id", None) if employee is not None else None
    if user_id and user_has_person_blocks(user_id):
        return user_id
    return None


class PersonBlockProxy:
    """Bloco da pessoa com a mesma forma de um `WorkJourneyBlock`, para os consumidores legados.

    Nao e uma entidade do banco: nunca e adicionada a sessao nem gravada.
    """

    is_person = True

    def __init__(self, block: PersonWorkBlock, company_id: int | None = None, employee_id: int | None = None):
        self.id = block.id
        self.company_id = company_id
        self.employee_id = employee_id
        self.name = block.name
        self.description = block.description
        self.start_time = block.start_time
        self.end_time = block.end_time
        self.block_mode = block.block_mode or "operational"
        self.weekdays_json = list(block.weekdays_json or [])
        self.accepted_item_types = list(ALL_ITEM_TYPES)  # o bloco da pessoa aceita qualquer item
        self.preferred_item_types = list(block.preferred_item_types or [])
        self.order_index = int(block.order_index or 0)
        self.is_active = bool(block.is_active)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "start_time": self.start_time.strftime("%H:%M"), "end_time": self.end_time.strftime("%H:%M"),
            "block_mode": self.block_mode, "weekdays": list(self.weekdays_json), "accepted_item_types": list(self.accepted_item_types),
            "order_index": self.order_index, "is_active": self.is_active, "source": SOURCE_PERSON,
        }


def person_block_proxies(user_id: int, company_id: int | None = None, employee_id: int | None = None) -> list[PersonBlockProxy]:
    rows = (
        PersonWorkBlock.query.filter_by(user_id=user_id, is_active=True)
        .order_by(PersonWorkBlock.order_index.asc(), PersonWorkBlock.start_time.asc(), PersonWorkBlock.id.asc())
        .all()
    )
    return [PersonBlockProxy(b, company_id, employee_id) for b in rows]


class PersonModeView:
    """Envolve uma entrada de agenda ou evento: `block_id`/`block` passam a apontar para o bloco da PESSOA.

    Entradas antigas que so tem `block_id` legado ficam sem bloco (aparecem como "sem bloco").
    Leitura apenas; a entidade original nao e alterada.
    """

    def __init__(self, obj: Any, blocks_by_id: dict[int, PersonBlockProxy]):
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_block", blocks_by_id.get(getattr(obj, "person_block_id", None)))

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_obj"), name)

    @property
    def block(self):
        return object.__getattribute__(self, "_block")

    @property
    def block_id(self):
        block = object.__getattribute__(self, "_block")
        return block.id if block is not None else None


PERSON_MODE_NOTE = (
    "Este colaborador usa blocos da pessoa. Os blocos por empresa abaixo continuam guardados, mas nao definem mais o dia dele; "
    "edite os blocos da pessoa em Agenda > Meus blocos."
)


def person_mode_extras(company_id: int, employee_id: int | None, *, with_blocks: bool = True) -> dict[str, Any]:
    """Campos ADITIVOS para respostas de blocos legados. Vazio quando o colaborador nao migrou (contrato intacto)."""
    if not employee_id:
        return {}
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    user_id = person_mode_user(employee)
    if user_id is None:
        return {}
    extras: dict[str, Any] = {"person_mode": True, "person_mode_note": PERSON_MODE_NOTE}
    if with_blocks:
        extras["person_blocks"] = [b.to_dict() for b in person_block_proxies(user_id, company_id, employee_id)]
    return extras
