from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func

from models import db, Process, ProcessRoutine

ACTIVITY_CODE_NAME_RE = re.compile(
    r"^\s*([A-Z]{1,6}(?:\.[A-Z0-9]+)+\.\d{2})\s*[-–—:]\s*(.+?)\s*$"
)


def open_or_create_pop_activity_for_bpmn(
    *,
    process: Process,
    payload: dict[str, Any],
) -> tuple[ProcessRoutine, bool]:
    """Open existing or create a POP activity linked to one BPMN activity.

    The binding key is tenant-safe by construction:
    company_id + process_id + bpmn_element_id.
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload inválido.")

    bpmn_element_id = _clean_text(payload.get("bpmn_element_id") or payload.get("id"))
    if not bpmn_element_id:
        raise ValueError("bpmn_element_id é obrigatório.")

    bpmn_element_type = _clean_text(payload.get("bpmn_element_type") or payload.get("type"))
    raw_bpmn_element_name = _clean_text(payload.get("bpmn_element_name") or payload.get("name"))
    business_code, bpmn_element_name = split_activity_business_code_and_name(
        raw_bpmn_element_name,
        process_code=process.code,
        fallback_code=bpmn_element_id,
    )
    bpmn_element_name = (
        _strip_bpmn_code_prefix(bpmn_element_name, bpmn_element_id)
        or _default_activity_name(business_code or bpmn_element_id)
    )
    routine_code = business_code or bpmn_element_id
    data_objects = _normalize_data_objects(payload.get("data_objects"))

    existing = (
        ProcessRoutine.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            bpmn_element_id=bpmn_element_id,
        )
        .filter((ProcessRoutine.is_active.is_(True)) | (ProcessRoutine.is_active.is_(None)))
        .order_by(ProcessRoutine.id.asc())
        .first()
    )
    if existing:
        existing.code = routine_code or existing.code
        existing.name = _strip_bpmn_code_prefix(existing.name, bpmn_element_id) or bpmn_element_name
        normalized_code, normalized_name = split_activity_business_code_and_name(
            existing.name,
            process_code=process.code,
            fallback_code=existing.code,
        )
        if normalized_code:
            existing.code = normalized_code
            existing.name = normalized_name or existing.name
        existing.bpmn_element_type = bpmn_element_type or existing.bpmn_element_type
        existing.bpmn_data_objects = data_objects or existing.bpmn_data_objects
        db.session.commit()
        _ensure_generic_pop_artifact(existing)
        return existing, False

    next_order = (
        db.session.query(func.coalesce(func.max(ProcessRoutine.order_index), 0))
        .filter_by(company_id=process.company_id, process_id=process.id)
        .scalar()
        or 0
    ) + 1

    routine = ProcessRoutine(
        company_id=process.company_id,
        process_id=process.id,
        code=routine_code,
        name=bpmn_element_name,
        description=_build_description(bpmn_element_id=bpmn_element_id, data_objects=data_objects),
        order_index=next_order,
        bpmn_element_id=bpmn_element_id,
        bpmn_element_type=bpmn_element_type,
        bpmn_data_objects=data_objects,
        is_active=True,
    )
    db.session.add(routine)
    db.session.commit()
    _ensure_generic_pop_artifact(routine)
    return routine, True


def _ensure_generic_pop_artifact(routine: ProcessRoutine) -> None:
    # Import local evita ciclo entre o adaptador legado e o catálogo genérico.
    from services.process_artifact_service import ensure_pop_artifact_for_routine

    ensure_pop_artifact_for_routine(routine)


def serialize_pop_binding(routine: ProcessRoutine, *, created: bool) -> dict[str, Any]:
    return {
        "created": created,
        "routine": {
            "id": routine.id,
            "company_id": routine.company_id,
            "process_id": routine.process_id,
            "code": routine.code,
            "name": routine.name,
            "description": routine.description,
            "order_index": routine.order_index,
            "bpmn_element_id": routine.bpmn_element_id,
            "bpmn_element_type": routine.bpmn_element_type,
            "bpmn_data_objects": routine.bpmn_data_objects or [],
        },
    }


def _build_description(*, bpmn_element_id: str, data_objects: list[dict[str, str]]) -> str:
    data_object_names = [
        item.get("name") or item.get("id")
        for item in data_objects
        if item.get("name") or item.get("id")
    ]
    details = ", ".join(data_object_names) if data_object_names else "Data Object Reference associado"
    return (
        "Atividade POP criada a partir do APP32 BPMN Modeler.\n\n"
        f"Elemento BPMN: {bpmn_element_id}\n"
        f"Marcador POP: {details}\n\n"
        "Complete este POP com os passos, evidências, prints e critérios de aceite da execução."
    )


def _normalize_data_objects(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        data_object_id = _clean_text(item.get("id"))
        if not data_object_id:
            continue
        normalized.append(
            {
                "id": data_object_id,
                "name": _clean_text(item.get("name")) or data_object_id,
                "type": _clean_text(item.get("type")) or "DataObjectReference",
            }
        )
    return normalized


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def split_activity_business_code_and_name(
    value: Any,
    *,
    process_code: str | None = None,
    fallback_code: str | None = None,
) -> tuple[str | None, str | None]:
    """Extrai código APP32 e nome humano de labels BPMN no padrão CODIGO - Nome.

    Exemplo legado de produção:
      value='AA.C.1.1.2.04 - Atividade 04', fallback_code='Activity_03y9xr2'
      -> ('AA.C.1.1.2.04', 'Atividade 04')
    """
    text = _clean_text(value)
    fallback_code = _clean_text(fallback_code)
    if text:
        match = ACTIVITY_CODE_NAME_RE.match(text)
        if match:
            candidate_code = match.group(1).strip()
            candidate_name = _clean_text(match.group(2))
            return candidate_code, candidate_name

    if fallback_code and not _is_generated_bpmn_id(fallback_code):
        return fallback_code, _strip_bpmn_code_prefix(text, fallback_code) if text else None

    return fallback_code, text


def _is_generated_bpmn_id(value: str | None) -> bool:
    return bool(
        value
        and re.match(r"^(Activity|Task|SubProcess|CallActivity)_[A-Za-z0-9]+$", value)
    )


def _strip_bpmn_code_prefix(value: Any, code: str) -> str | None:
    text = _clean_text(value)
    code = _clean_text(code)
    if not text or not code:
        return text
    if text == code:
        return None
    prefixes = (
        f"{code} - ",
        f"{code}-",
        f"{code} – ",
        f"{code} — ",
        f"{code}: ",
    )
    for prefix in prefixes:
        if text.startswith(prefix):
            return _clean_text(text[len(prefix):])
    return text


def _default_activity_name(code: str) -> str:
    suffix = (_clean_text(code) or "").split(".")[-1]
    if suffix.isdigit():
        return f"Atividade {suffix}"
    return "Atividade"
