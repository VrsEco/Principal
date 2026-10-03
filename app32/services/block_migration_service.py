"""Assistente de migracao dos blocos por empresa para os blocos da pessoa (SPEC secao 10).

- Iniciado pelo proprio usuario; nunca em lote. Nada e criado sem confirmacao de cada proposta.
- Blocos de mesmo nome e modo, e que se sobrepoem nos dias em comum, viram um so (horario mais amplo).
- Reversivel: os blocos legados ficam intactos; excluir os blocos da pessoa devolve o comportamento anterior.
- Quem nao tem usuario vinculado segue com blocos por empresa.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

from models import (
    Company,
    Employee,
    PersonWorkBlock,
    RoutineJourneyBinding,
    UserLog,
    WorkCalendarEvent,
    WorkJourneyAgendaItem,
    WorkJourneyBlock,
    db,
)
from services import person_work_block_service as person_blocks
from services.person_work_block_service import PersonBlockError

MODE_LABELS = {"operational": "Operacional", "reserved_full": "Capacidade ocupada", "buffer": "Vazio / Buffer"}


def normalize_name(name: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _minutes(value) -> int:
    return value.hour * 60 + value.minute


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def group_legacy_blocks(blocks: Iterable[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Agrupa blocos legados: mesmo nome normalizado, mesmo modo e janelas que se sobrepoem em dias comuns.

    Cada bloco: {name, mode, start_minutes, end_minutes, weekdays, ...}. Devolve listas de blocos.
    """
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for block in blocks:
        buckets.setdefault((normalize_name(block["name"]), block["mode"]), []).append(block)

    groups: list[list[dict[str, Any]]] = []
    for members in buckets.values():
        clusters: list[list[dict[str, Any]]] = []
        for block in sorted(members, key=lambda b: (b["start_minutes"], b["end_minutes"])):
            target = None
            for cluster in clusters:
                if any(_overlap_on_common_days(block, other) for other in cluster):
                    target = cluster
                    break
            if target is None:
                clusters.append([block])
            else:
                target.append(block)
        groups.extend(clusters)
    return groups


def _overlap_on_common_days(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if not set(a["weekdays"]) & set(b["weekdays"]):
        return False
    return a["start_minutes"] < b["end_minutes"] and b["start_minutes"] < a["end_minutes"]


def _employee_scope(user_id: int) -> list[Employee]:
    return Employee.query.filter(Employee.user_id == user_id, Employee.status == "active").all()


def propose(user_id: int) -> dict[str, Any]:
    """Proposta de lista unica de blocos da pessoa. Nao grava nada."""
    if person_blocks.has_blocks(user_id):
        return {"already_migrated": True, "proposals": [], "legacy_count": 0, "companies": 0}
    employees = {e.id: e for e in _employee_scope(user_id)}
    if not employees:
        return {"already_migrated": False, "proposals": [], "legacy_count": 0, "companies": 0}
    company_names = {c.id: c.name for c in Company.query.filter(Company.id.in_({e.company_id for e in employees.values()})).all()}
    rows = WorkJourneyBlock.query.filter(WorkJourneyBlock.employee_id.in_(employees), WorkJourneyBlock.is_active.is_(True)).all()
    legacy = [
        {
            "block_id": b.id,
            "employee_id": b.employee_id,
            "company_id": b.company_id,
            "company": company_names.get(b.company_id),
            "name": b.name,
            "mode": b.block_mode or "operational",
            "start_minutes": _minutes(b.start_time),
            "end_minutes": _minutes(b.end_time),
            "weekdays": sorted({int(d) for d in (b.weekdays_json or [])}),
            "types": list(b.accepted_item_types or []),
        }
        for b in rows
    ]
    proposals = []
    for index, members in enumerate(sorted(group_legacy_blocks(legacy), key=lambda g: min(m["start_minutes"] for m in g)), start=1):
        start = min(m["start_minutes"] for m in members)
        end = max(m["end_minutes"] for m in members)
        names = sorted({m["name"] for m in members})
        differing = len({(m["start_minutes"], m["end_minutes"]) for m in members}) > 1
        proposals.append(
            {
                "id": index,
                "name": names[0],
                "mode": members[0]["mode"],
                "start": _hhmm(start),
                "end": _hhmm(end),
                "weekdays": sorted({d for m in members for d in m["weekdays"]}),
                "preferred_item_types": sorted({t for m in members for t in m["types"]}),
                "merged": len(members) > 1,
                "note": ("Horários diferentes entre empresas: usamos a janela mais ampla." if differing else None),
                "sources": [
                    {"block_id": m["block_id"], "company": m["company"], "name": m["name"], "start": _hhmm(m["start_minutes"]), "end": _hhmm(m["end_minutes"])}
                    for m in members
                ],
            }
        )
    return {"already_migrated": False, "proposals": proposals, "legacy_count": len(legacy), "companies": len(company_names)}


def apply(user_id: int, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria os blocos confirmados (com ajustes) e reaponta vinculos de rotina. Recusadas nao criam nada."""
    if person_blocks.has_blocks(user_id):
        raise PersonBlockError("Você já usa blocos da pessoa. Edite-os na tela de blocos ou volte aos blocos por empresa.")
    plan = {p["id"]: p for p in propose(user_id)["proposals"]}
    accepted = [d for d in (decisions or []) if d.get("accept", True) and d.get("id") in plan]
    if not accepted:
        raise PersonBlockError("Confirme ao menos uma proposta.")

    created = []
    rebound = 0
    for decision in accepted:
        base = plan[decision["id"]]
        payload = {
            "name": decision.get("name") or base["name"],
            "start": decision.get("start") or base["start"],
            "end": decision.get("end") or base["end"],
            "mode": decision.get("mode") or base["mode"],
            "weekdays": decision.get("weekdays") or base["weekdays"],
            "preferred_item_types": decision.get("preferred_item_types", base["preferred_item_types"]),
        }
        result = person_blocks.create_block(user_id, payload)
        new_id = result["block"]["id"]
        created.append(result["block"])
        source_ids = [s["block_id"] for s in base["sources"]]
        employee_ids = [e.id for e in _employee_scope(user_id)]
        bindings = RoutineJourneyBinding.query.filter(
            RoutineJourneyBinding.employee_id.in_(employee_ids), RoutineJourneyBinding.block_id.in_(source_ids)
        ).all()
        for binding in bindings:
            binding.person_block_id = new_id
            rebound += 1
    db.session.commit()
    return {"created": created, "routines_rebound": rebound, "warnings": person_blocks.list_blocks(user_id)["warnings"]}


def revert(user_id: int) -> dict[str, Any]:
    """Volta aos blocos por empresa. Os blocos legados nunca foram alterados."""
    ids = [b.id for b in PersonWorkBlock.query.filter_by(user_id=user_id).all()]
    if not ids:
        return {"removed": 0, "released_entries": 0}
    employee_ids = [e.id for e in _employee_scope(user_id)]
    released = 0
    entries = WorkJourneyAgendaItem.query.filter(
        WorkJourneyAgendaItem.employee_id.in_(employee_ids), WorkJourneyAgendaItem.person_block_id.in_(ids)
    ).all()
    for entry in entries:
        entry.person_block_id = None
        if entry.block_id is None:
            entry.manual_override = False  # o motor volta a sugerir; nada fica preso a um bloco que não existe mais
            released += 1
    RoutineJourneyBinding.query.filter(RoutineJourneyBinding.person_block_id.in_(ids)).update({"person_block_id": None}, synchronize_session=False)
    WorkCalendarEvent.query.filter(WorkCalendarEvent.person_block_id.in_(ids)).update({"person_block_id": None}, synchronize_session=False)
    result = person_blocks.delete_all_blocks(user_id)
    return {"removed": result["removed"], "released_entries": released}
