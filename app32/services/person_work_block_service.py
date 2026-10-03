"""Blocos de jornada da pessoa: cadastro, validacao, avisos de sobreposicao e auditoria.

SPEC agenda unificada, secoes 5.3 e 6.1. Cada bloco pertence ao USUARIO (sem company_id);
so o proprio usuario le e grava. Sobreposicao gera AVISO, nunca impede (RF-BLO-5).
"""

from __future__ import annotations

import json
from datetime import time
from typing import Any, Iterable

from models import PersonWorkBlock, UserLog, db

MODES = ("operational", "reserved_full", "buffer")
ITEM_TYPES = ("manual", "process_instance", "project_task", "meeting")
MAX_BLOCKS_PER_USER = 60
AUDIT_ENTITY = "person_work_block"


class PersonBlockError(ValueError):
    pass


def _parse_time(value: Any, label: str) -> time:
    try:
        hours, minutes = str(value).split(":")[:2]
        return time(int(hours), int(minutes))
    except (ValueError, TypeError):
        raise PersonBlockError(f"{label} inválido. Use HH:MM.")


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normaliza e valida os campos de um bloco (RF-BLO-2)."""
    name = str(payload.get("name") or "").strip()
    if not name:
        raise PersonBlockError("Informe o nome do bloco.")
    if len(name) > 160:
        raise PersonBlockError("O nome do bloco pode ter até 160 caracteres.")
    start = _parse_time(payload.get("start"), "Horário de início")
    end = _parse_time(payload.get("end"), "Horário de fim")
    if _minutes(end) <= _minutes(start):
        raise PersonBlockError("O fim do bloco deve ser depois do início.")
    mode = str(payload.get("mode") or "operational")
    if mode not in MODES:
        raise PersonBlockError("Modo inválido.")
    try:
        weekdays = sorted({int(d) for d in (payload.get("weekdays") or [])})
    except (TypeError, ValueError):
        raise PersonBlockError("Dias da semana inválidos.")
    if not weekdays or any(d < 0 or d > 6 for d in weekdays):
        raise PersonBlockError("Escolha ao menos um dia da semana.")
    types = [t for t in (payload.get("preferred_item_types") or []) if t in ITEM_TYPES]
    return {
        "name": name,
        "description": (str(payload.get("description") or "").strip() or None),
        "start_time": start,
        "end_time": end,
        "block_mode": mode,
        "weekdays_json": weekdays,
        "preferred_item_types": sorted(set(types)),
        "is_active": bool(payload.get("is_active", True)),
    }


def union_minutes(intervals: Iterable[tuple[int, int]]) -> int:
    """Total de minutos da UNIAO dos intervalos: a mesma hora nao conta duas vezes (RF-BLO-5)."""
    total, cur_start, cur_end = 0, None, None
    for start, end in sorted((s, e) for s, e in intervals if e > s):
        if cur_end is None or start > cur_end:
            if cur_end is not None:
                total += cur_end - cur_start
            cur_start, cur_end = start, end
        else:
            cur_end = max(cur_end, end)
    if cur_end is not None:
        total += cur_end - cur_start
    return total


def overlap_warnings(blocks: Iterable[Any]) -> list[dict[str, Any]]:
    """Pares de blocos ativos que se sobrepoem em algum dia da semana. So avisa."""
    active = [b for b in blocks if getattr(b, "is_active", True)]
    warnings: list[dict[str, Any]] = []
    for i, a in enumerate(active):
        for b in active[i + 1:]:
            days = sorted(set(a.weekdays_json or []) & set(b.weekdays_json or []))
            if not days:
                continue
            if _minutes(a.start_time) < _minutes(b.end_time) and _minutes(b.start_time) < _minutes(a.end_time):
                warnings.append(
                    {
                        "a": {"id": a.id, "name": a.name},
                        "b": {"id": b.id, "name": b.name},
                        "weekdays": days,
                        "message": f"“{a.name}” e “{b.name}” se sobrepõem. A capacidade conta cada hora uma vez.",
                    }
                )
    return warnings


def _audit(user_id: int, action: str, block: PersonWorkBlock | None, old: dict | None, new: dict | None, description: str) -> None:
    from flask import has_request_context, request

    from flask_login import current_user

    actor = current_user if getattr(current_user, "is_authenticated", False) else None
    db.session.add(
        UserLog(
            user_id=user_id,
            user_email=str(getattr(actor, "email", "") or "desconhecido"),
            user_name=str(getattr(actor, "name", None) or getattr(actor, "username", None) or "Usuário"),
            action=action,
            entity_type=AUDIT_ENTITY,
            entity_id=str(block.id) if block is not None and block.id is not None else "",
            entity_name=(block.name if block is not None else None),
            old_values=json.dumps(old or {}, ensure_ascii=False, default=str),
            new_values=json.dumps(new or {}, ensure_ascii=False, default=str),
            ip_address=(request.remote_addr if has_request_context() else None),
            endpoint=(request.path if has_request_context() else None),
            method=(request.method if has_request_context() else None),
            description=description,
        )
    )


def _snapshot(block: PersonWorkBlock) -> dict[str, Any]:
    return block.to_dict()


def list_blocks(user_id: int, *, include_inactive: bool = True) -> dict[str, Any]:
    query = PersonWorkBlock.query.filter_by(user_id=user_id)
    if not include_inactive:
        query = query.filter_by(is_active=True)
    blocks = query.order_by(PersonWorkBlock.order_index, PersonWorkBlock.start_time, PersonWorkBlock.id).all()
    return {"blocks": [b.to_dict() for b in blocks], "warnings": overlap_warnings(blocks)}


def has_blocks(user_id: int | None) -> bool:
    if not user_id:
        return False
    return db.session.query(PersonWorkBlock.id).filter_by(user_id=user_id, is_active=True).first() is not None


def _get(user_id: int, block_id: int) -> PersonWorkBlock:
    block = PersonWorkBlock.query.filter_by(id=block_id, user_id=user_id).first()
    if block is None:
        raise PersonBlockError("Bloco não encontrado.")
    return block


def create_block(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    data = validate_payload(payload)
    if PersonWorkBlock.query.filter_by(user_id=user_id).count() >= MAX_BLOCKS_PER_USER:
        raise PersonBlockError("Limite de blocos atingido.")
    order = (db.session.query(db.func.max(PersonWorkBlock.order_index)).filter_by(user_id=user_id).scalar() or 0) + 1
    block = PersonWorkBlock(user_id=user_id, order_index=order, **data)
    db.session.add(block)
    db.session.flush()
    _audit(user_id, "create", block, None, _snapshot(block), f"Bloco da pessoa criado: {block.name}")
    db.session.commit()
    return {"block": block.to_dict(), "warnings": overlap_warnings(PersonWorkBlock.query.filter_by(user_id=user_id).all())}


def update_block(user_id: int, block_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    block = _get(user_id, block_id)
    old = _snapshot(block)
    for key, value in validate_payload({**old, **payload, "start": payload.get("start", old["start"]), "end": payload.get("end", old["end"])}).items():
        setattr(block, key, value)
    db.session.flush()
    _audit(user_id, "update", block, old, _snapshot(block), f"Bloco da pessoa alterado: {block.name}")
    db.session.commit()
    return {"block": block.to_dict(), "warnings": overlap_warnings(PersonWorkBlock.query.filter_by(user_id=user_id).all())}


def delete_block(user_id: int, block_id: int) -> dict[str, Any]:
    block = _get(user_id, block_id)
    old = _snapshot(block)
    name = block.name
    db.session.delete(block)
    _audit(user_id, "delete", None, old, None, f"Bloco da pessoa excluído: {name}")
    db.session.commit()
    return {"deleted": block_id}


def reorder_blocks(user_id: int, ids: list[int]) -> dict[str, Any]:
    blocks = {b.id: b for b in PersonWorkBlock.query.filter_by(user_id=user_id).all()}
    if set(ids) != set(blocks):
        raise PersonBlockError("Informe todos os seus blocos na nova ordem.")
    old = {i: blocks[i].order_index for i in ids}
    for position, block_id in enumerate(ids, start=1):
        blocks[block_id].order_index = position
    _audit(user_id, "reorder", None, {"order": old}, {"order": {i: p for p, i in enumerate(ids, start=1)}}, "Blocos da pessoa reordenados")
    db.session.commit()
    return list_blocks(user_id)


def delete_all_blocks(user_id: int) -> dict[str, Any]:
    """Reverte para o comportamento anterior: os blocos legados nunca foram tocados."""
    blocks = PersonWorkBlock.query.filter_by(user_id=user_id).all()
    removed = len(blocks)
    for block in blocks:
        db.session.delete(block)
    _audit(user_id, "delete_all", None, {"count": removed}, None, "Blocos da pessoa excluídos (volta aos blocos por empresa)")
    db.session.commit()
    return {"removed": removed}
