from __future__ import annotations

from datetime import datetime
from sqlalchemy import case

from models import (
    db,
    Process,
    ProcessSipocItem,
    ProcessSipocRegulatoryItem,
    ProcessSipocSnapshot,
)


VALID_LANES = ("supplier", "input", "process", "output", "customer")
VALID_RISK_LEVELS = ("low", "medium", "high", "critical")
VALID_SCOPE_TYPES = ("process", "lane_item")
VALID_SOURCE_TYPES = ("manual", "bpmn", "indicator", "bpms")


def get_process_or_raise(process_id: int, company_id: int) -> Process:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if not process:
        raise ValueError("Processo não encontrado para a empresa ativa.")
    return process


def get_process_sipoc_bundle(*, process_id: int, company_id: int) -> dict:
    process = get_process_or_raise(process_id, company_id)
    draft = (
        ProcessSipocSnapshot.query
        .filter_by(process_id=process.id, company_id=company_id, status='draft')
        .order_by(ProcessSipocSnapshot.updated_at.desc(), ProcessSipocSnapshot.id.desc())
        .first()
    )
    published = (
        ProcessSipocSnapshot.query
        .filter_by(process_id=process.id, company_id=company_id, status='published')
        .order_by(ProcessSipocSnapshot.version.desc(), ProcessSipocSnapshot.id.desc())
        .first()
    )

    return {
        "process_id": process.id,
        "company_id": company_id,
        "draft_snapshot": serialize_snapshot(draft) if draft else None,
        "published_snapshot": serialize_snapshot(published) if published else None,
        "current_snapshot": serialize_snapshot(draft or published) if (draft or published) else None,
        "has_sipoc": bool(draft or published),
    }


def create_sipoc_draft(*, process_id: int, company_id: int, user_id: int | None) -> dict:
    process = get_process_or_raise(process_id, company_id)

    existing_draft = (
        ProcessSipocSnapshot.query
        .filter_by(process_id=process.id, company_id=company_id, status='draft')
        .order_by(ProcessSipocSnapshot.updated_at.desc(), ProcessSipocSnapshot.id.desc())
        .first()
    )
    if existing_draft:
        return serialize_snapshot(existing_draft)

    published = (
        ProcessSipocSnapshot.query
        .filter_by(process_id=process.id, company_id=company_id, status='published')
        .order_by(ProcessSipocSnapshot.version.desc(), ProcessSipocSnapshot.id.desc())
        .first()
    )
    next_version = int((published.version if published else 0) or 0) + 1

    snapshot = ProcessSipocSnapshot(
        company_id=company_id,
        process_id=process.id,
        version=next_version,
        status='draft',
        title=_default_title(process),
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.session.add(snapshot)
    db.session.flush()

    if published:
        _copy_snapshot_children(published, snapshot)
        snapshot.objective = published.objective
        snapshot.start_boundary = published.start_boundary
        snapshot.end_boundary = published.end_boundary
        snapshot.trigger_event = published.trigger_event
        snapshot.customer_requirements = published.customer_requirements
        snapshot.constraints_notes = published.constraints_notes
        snapshot.measures_notes = published.measures_notes
        snapshot.risks_notes = published.risks_notes
        snapshot.notes = published.notes

    db.session.commit()
    return serialize_snapshot(snapshot)


def update_sipoc_snapshot(*, process_id: int, company_id: int, sipoc_id: int, data: dict, user_id: int | None) -> dict:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    fields = (
        "title",
        "objective",
        "start_boundary",
        "end_boundary",
        "trigger_event",
        "customer_requirements",
        "constraints_notes",
        "measures_notes",
        "risks_notes",
        "notes",
    )
    for field in fields:
        if field in data:
            setattr(snapshot, field, _normalize_text(data.get(field)))
    snapshot.updated_by_user_id = user_id
    db.session.commit()
    return serialize_snapshot(snapshot)


def create_sipoc_item(*, process_id: int, company_id: int, sipoc_id: int, data: dict) -> dict:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    lane = _normalize_lane(data.get("lane"))
    item = ProcessSipocItem(
        company_id=company_id,
        sipoc_snapshot_id=snapshot.id,
        lane=lane,
        title=_require_text(data.get("title"), "Título do item é obrigatório."),
        description=_normalize_text(data.get("description")),
        order_index=_coerce_order_index(data.get("order_index"), lane=lane, snapshot_id=snapshot.id),
        source_type=_normalize_source_type(data.get("source_type")),
        source_ref=_normalize_text(data.get("source_ref")),
        is_critical=bool(data.get("is_critical")),
    )
    db.session.add(item)
    db.session.commit()
    return serialize_item(item)


def update_sipoc_item(*, process_id: int, company_id: int, sipoc_id: int, item_id: int, data: dict) -> dict:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    item = _get_item_in_snapshot(snapshot.id, company_id, item_id)
    if "lane" in data:
        item.lane = _normalize_lane(data.get("lane"))
    if "title" in data:
        item.title = _require_text(data.get("title"), "Título do item é obrigatório.")
    if "description" in data:
        item.description = _normalize_text(data.get("description"))
    if "order_index" in data:
        item.order_index = _coerce_order_index(data.get("order_index"), lane=item.lane, snapshot_id=snapshot.id)
    if "source_type" in data:
        item.source_type = _normalize_source_type(data.get("source_type"))
    if "source_ref" in data:
        item.source_ref = _normalize_text(data.get("source_ref"))
    if "is_critical" in data:
        item.is_critical = bool(data.get("is_critical"))
    db.session.commit()
    return serialize_item(item)


def delete_sipoc_item(*, process_id: int, company_id: int, sipoc_id: int, item_id: int) -> None:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    item = _get_item_in_snapshot(snapshot.id, company_id, item_id)
    db.session.delete(item)
    db.session.commit()


def create_regulatory_item(*, process_id: int, company_id: int, sipoc_id: int, data: dict) -> dict:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    sipoc_item_id = _validate_optional_item_reference(snapshot.id, company_id, data.get("sipoc_item_id"))
    reg = ProcessSipocRegulatoryItem(
        company_id=company_id,
        sipoc_snapshot_id=snapshot.id,
        sipoc_item_id=sipoc_item_id,
        regulatory_domain=_require_text(data.get("regulatory_domain"), "Domínio regulatório é obrigatório."),
        regulatory_code=_normalize_text(data.get("regulatory_code")),
        regulatory_name=_require_text(data.get("regulatory_name"), "Nome da norma/regra é obrigatório."),
        regulator_entity=_normalize_text(data.get("regulator_entity")),
        requirement_summary=_normalize_text(data.get("requirement_summary")),
        affected_scope_type=_normalize_scope_type(data.get("affected_scope_type"), sipoc_item_id),
        control_requirements=_normalize_text(data.get("control_requirements")),
        risk_level=_normalize_risk_level(data.get("risk_level")),
        evidence_requirements=_normalize_text(data.get("evidence_requirements")),
        notes=_normalize_text(data.get("notes")),
    )
    db.session.add(reg)
    db.session.commit()
    return serialize_regulatory_item(reg)


def update_regulatory_item(*, process_id: int, company_id: int, sipoc_id: int, regulatory_item_id: int, data: dict) -> dict:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    reg = _get_regulatory_item_in_snapshot(snapshot.id, company_id, regulatory_item_id)

    if "sipoc_item_id" in data:
        reg.sipoc_item_id = _validate_optional_item_reference(snapshot.id, company_id, data.get("sipoc_item_id"))
    if "regulatory_domain" in data:
        reg.regulatory_domain = _require_text(data.get("regulatory_domain"), "Domínio regulatório é obrigatório.")
    if "regulatory_code" in data:
        reg.regulatory_code = _normalize_text(data.get("regulatory_code"))
    if "regulatory_name" in data:
        reg.regulatory_name = _require_text(data.get("regulatory_name"), "Nome da norma/regra é obrigatório.")
    if "regulator_entity" in data:
        reg.regulator_entity = _normalize_text(data.get("regulator_entity"))
    if "requirement_summary" in data:
        reg.requirement_summary = _normalize_text(data.get("requirement_summary"))
    if "affected_scope_type" in data or "sipoc_item_id" in data:
        reg.affected_scope_type = _normalize_scope_type(data.get("affected_scope_type", reg.affected_scope_type), reg.sipoc_item_id)
    if "control_requirements" in data:
        reg.control_requirements = _normalize_text(data.get("control_requirements"))
    if "risk_level" in data:
        reg.risk_level = _normalize_risk_level(data.get("risk_level"))
    if "evidence_requirements" in data:
        reg.evidence_requirements = _normalize_text(data.get("evidence_requirements"))
    if "notes" in data:
        reg.notes = _normalize_text(data.get("notes"))

    db.session.commit()
    return serialize_regulatory_item(reg)


def delete_regulatory_item(*, process_id: int, company_id: int, sipoc_id: int, regulatory_item_id: int) -> None:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    reg = _get_regulatory_item_in_snapshot(snapshot.id, company_id, regulatory_item_id)
    db.session.delete(reg)
    db.session.commit()


def publish_sipoc_snapshot(*, process_id: int, company_id: int, sipoc_id: int, user_id: int | None) -> dict:
    snapshot = _get_snapshot_for_update(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    errors = validate_snapshot_for_publish(snapshot)
    if errors:
        raise ValueError(" ; ".join(errors))

    published_snapshots = (
        ProcessSipocSnapshot.query
        .filter_by(process_id=process_id, company_id=company_id, status='published')
        .filter(ProcessSipocSnapshot.id != snapshot.id)
        .all()
    )
    for published in published_snapshots:
        published.status = 'archived'
        published.updated_by_user_id = user_id

    snapshot.status = 'published'
    snapshot.published_at = datetime.utcnow()
    snapshot.updated_by_user_id = user_id
    db.session.commit()
    return serialize_snapshot(snapshot)


def archive_sipoc_snapshot(*, process_id: int, company_id: int, sipoc_id: int, user_id: int | None) -> dict:
    snapshot = _get_snapshot_in_company(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    snapshot.status = 'archived'
    snapshot.updated_by_user_id = user_id
    db.session.commit()
    return serialize_snapshot(snapshot)


def validate_snapshot_for_publish(snapshot: ProcessSipocSnapshot) -> list[str]:
    errors: list[str] = []
    if not _normalize_text(snapshot.start_boundary):
        errors.append("Preencha o início do processo.")
    if not _normalize_text(snapshot.end_boundary):
        errors.append("Preencha o fim do processo.")

    lane_counts = snapshot_lane_counts(snapshot)
    if lane_counts.get("supplier", 0) < 1:
        errors.append("Cadastre ao menos 1 fornecedor.")
    if lane_counts.get("input", 0) < 1:
        errors.append("Cadastre ao menos 1 entrada.")
    if lane_counts.get("process", 0) < 3:
        errors.append("Cadastre pelo menos 3 macroetapas no processo.")
    if lane_counts.get("process", 0) > 7:
        errors.append("O SIPOC recomenda no máximo 7 macroetapas no processo.")
    if lane_counts.get("output", 0) < 1:
        errors.append("Cadastre ao menos 1 saída.")
    if lane_counts.get("customer", 0) < 1:
        errors.append("Cadastre ao menos 1 cliente.")
    return errors


def snapshot_lane_counts(snapshot: ProcessSipocSnapshot) -> dict[str, int]:
    counts = {lane: 0 for lane in VALID_LANES}
    rows = (
        db.session.query(ProcessSipocItem.lane, db.func.count(ProcessSipocItem.id))
        .filter(ProcessSipocItem.sipoc_snapshot_id == snapshot.id)
        .group_by(ProcessSipocItem.lane)
        .all()
    )
    for lane, total in rows:
        counts[str(lane)] = int(total or 0)
    return counts


def serialize_snapshot(snapshot: ProcessSipocSnapshot | None) -> dict | None:
    if not snapshot:
        return None

    items = (
        ProcessSipocItem.query
        .filter_by(sipoc_snapshot_id=snapshot.id, company_id=snapshot.company_id)
        .order_by(
            case({lane: idx for idx, lane in enumerate(VALID_LANES)}, value=ProcessSipocItem.lane, else_=99),
            ProcessSipocItem.order_index.asc(),
            ProcessSipocItem.id.asc(),
        )
        .all()
    )
    regulatory_items = (
        ProcessSipocRegulatoryItem.query
        .filter_by(sipoc_snapshot_id=snapshot.id, company_id=snapshot.company_id)
        .order_by(ProcessSipocRegulatoryItem.id.asc())
        .all()
    )
    grouped_items = {lane: [] for lane in VALID_LANES}
    for item in items:
        grouped_items[item.lane].append(serialize_item(item))

    return {
        "id": snapshot.id,
        "company_id": snapshot.company_id,
        "process_id": snapshot.process_id,
        "version": snapshot.version,
        "status": snapshot.status,
        "title": snapshot.title,
        "objective": snapshot.objective,
        "start_boundary": snapshot.start_boundary,
        "end_boundary": snapshot.end_boundary,
        "trigger_event": snapshot.trigger_event,
        "customer_requirements": snapshot.customer_requirements,
        "constraints_notes": snapshot.constraints_notes,
        "measures_notes": snapshot.measures_notes,
        "risks_notes": snapshot.risks_notes,
        "notes": snapshot.notes,
        "created_by_user_id": snapshot.created_by_user_id,
        "updated_by_user_id": snapshot.updated_by_user_id,
        "published_at": _serialize_dt(snapshot.published_at),
        "created_at": _serialize_dt(snapshot.created_at),
        "updated_at": _serialize_dt(snapshot.updated_at),
        "items": grouped_items,
        "lane_counts": snapshot_lane_counts(snapshot),
        "regulatory_items": [serialize_regulatory_item(item) for item in regulatory_items],
        "publication_errors": validate_snapshot_for_publish(snapshot) if snapshot.status == 'draft' else [],
    }


def serialize_item(item: ProcessSipocItem) -> dict:
    return {
        "id": item.id,
        "company_id": item.company_id,
        "sipoc_snapshot_id": item.sipoc_snapshot_id,
        "lane": item.lane,
        "title": item.title,
        "description": item.description,
        "order_index": item.order_index,
        "source_type": item.source_type,
        "source_ref": item.source_ref,
        "is_critical": bool(item.is_critical),
        "created_at": _serialize_dt(item.created_at),
        "updated_at": _serialize_dt(item.updated_at),
    }


def serialize_regulatory_item(item: ProcessSipocRegulatoryItem) -> dict:
    return {
        "id": item.id,
        "company_id": item.company_id,
        "sipoc_snapshot_id": item.sipoc_snapshot_id,
        "sipoc_item_id": item.sipoc_item_id,
        "regulatory_domain": item.regulatory_domain,
        "regulatory_code": item.regulatory_code,
        "regulatory_name": item.regulatory_name,
        "regulator_entity": item.regulator_entity,
        "requirement_summary": item.requirement_summary,
        "affected_scope_type": item.affected_scope_type,
        "control_requirements": item.control_requirements,
        "risk_level": item.risk_level,
        "evidence_requirements": item.evidence_requirements,
        "notes": item.notes,
        "created_at": _serialize_dt(item.created_at),
        "updated_at": _serialize_dt(item.updated_at),
    }


def build_book_sipoc_context(*, process_id: int, company_id: int) -> dict | None:
    snapshot = (
        ProcessSipocSnapshot.query
        .filter_by(process_id=process_id, company_id=company_id, status='published')
        .order_by(ProcessSipocSnapshot.version.desc(), ProcessSipocSnapshot.id.desc())
        .first()
    )
    return serialize_snapshot(snapshot) if snapshot else None


def _copy_snapshot_children(source: ProcessSipocSnapshot, target: ProcessSipocSnapshot) -> None:
    item_map: dict[int, ProcessSipocItem] = {}
    source_items = (
        ProcessSipocItem.query
        .filter_by(sipoc_snapshot_id=source.id, company_id=source.company_id)
        .order_by(ProcessSipocItem.id.asc())
        .all()
    )
    for source_item in source_items:
        cloned = ProcessSipocItem(
            company_id=target.company_id,
            sipoc_snapshot_id=target.id,
            lane=source_item.lane,
            title=source_item.title,
            description=source_item.description,
            order_index=source_item.order_index,
            source_type=source_item.source_type,
            source_ref=source_item.source_ref,
            is_critical=source_item.is_critical,
        )
        db.session.add(cloned)
        db.session.flush()
        item_map[source_item.id] = cloned

    source_regs = (
        ProcessSipocRegulatoryItem.query
        .filter_by(sipoc_snapshot_id=source.id, company_id=source.company_id)
        .order_by(ProcessSipocRegulatoryItem.id.asc())
        .all()
    )
    for source_reg in source_regs:
        db.session.add(
            ProcessSipocRegulatoryItem(
                company_id=target.company_id,
                sipoc_snapshot_id=target.id,
                sipoc_item_id=item_map.get(source_reg.sipoc_item_id).id if source_reg.sipoc_item_id and item_map.get(source_reg.sipoc_item_id) else None,
                regulatory_domain=source_reg.regulatory_domain,
                regulatory_code=source_reg.regulatory_code,
                regulatory_name=source_reg.regulatory_name,
                regulator_entity=source_reg.regulator_entity,
                requirement_summary=source_reg.requirement_summary,
                affected_scope_type=source_reg.affected_scope_type,
                control_requirements=source_reg.control_requirements,
                risk_level=source_reg.risk_level,
                evidence_requirements=source_reg.evidence_requirements,
                notes=source_reg.notes,
            )
        )


def _get_snapshot_for_update(*, process_id: int, company_id: int, sipoc_id: int) -> ProcessSipocSnapshot:
    snapshot = _get_snapshot_in_company(process_id=process_id, company_id=company_id, sipoc_id=sipoc_id)
    if snapshot.status != 'draft':
        raise ValueError("Apenas rascunhos SIPOC podem ser editados.")
    return snapshot


def _get_snapshot_in_company(*, process_id: int, company_id: int, sipoc_id: int) -> ProcessSipocSnapshot:
    snapshot = (
        ProcessSipocSnapshot.query
        .filter_by(id=sipoc_id, process_id=process_id, company_id=company_id)
        .first()
    )
    if not snapshot:
        raise ValueError("SIPOC não encontrado para o processo informado.")
    return snapshot


def _get_item_in_snapshot(snapshot_id: int, company_id: int, item_id: int) -> ProcessSipocItem:
    item = (
        ProcessSipocItem.query
        .filter_by(id=item_id, sipoc_snapshot_id=snapshot_id, company_id=company_id)
        .first()
    )
    if not item:
        raise ValueError("Item SIPOC não encontrado.")
    return item


def _get_regulatory_item_in_snapshot(snapshot_id: int, company_id: int, regulatory_item_id: int) -> ProcessSipocRegulatoryItem:
    reg = (
        ProcessSipocRegulatoryItem.query
        .filter_by(id=regulatory_item_id, sipoc_snapshot_id=snapshot_id, company_id=company_id)
        .first()
    )
    if not reg:
        raise ValueError("Item regulatório não encontrado.")
    return reg


def _validate_optional_item_reference(snapshot_id: int, company_id: int, value) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        item_id = int(value)
    except (TypeError, ValueError):
        raise ValueError("Macroetapa vinculada inválida.")
    _get_item_in_snapshot(snapshot_id, company_id, item_id)
    return item_id


def _normalize_lane(value) -> str:
    lane = str(value or "").strip().lower()
    if lane not in VALID_LANES:
        raise ValueError("Lane SIPOC inválida.")
    return lane


def _normalize_risk_level(value) -> str:
    risk = str(value or "medium").strip().lower()
    if risk not in VALID_RISK_LEVELS:
        raise ValueError("Nível de criticidade regulatória inválido.")
    return risk


def _normalize_scope_type(value, sipoc_item_id: int | None) -> str:
    scope = str(value or ("lane_item" if sipoc_item_id else "process")).strip().lower()
    if scope not in VALID_SCOPE_TYPES:
        raise ValueError("Escopo regulatório inválido.")
    if scope == "lane_item" and not sipoc_item_id:
        raise ValueError("Selecione uma macroetapa vinculada para o escopo lane_item.")
    return scope


def _normalize_source_type(value) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    if normalized not in VALID_SOURCE_TYPES:
        raise ValueError("Origem do item SIPOC inválida.")
    return normalized


def _coerce_order_index(value, *, lane: str, snapshot_id: int) -> int:
    if value in (None, ""):
        current_max = (
            db.session.query(db.func.max(ProcessSipocItem.order_index))
            .filter(ProcessSipocItem.sipoc_snapshot_id == snapshot_id, ProcessSipocItem.lane == lane)
            .scalar()
        )
        return int(current_max or 0) + 1
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Ordem do item SIPOC inválida.")


def _require_text(value, message: str) -> str:
    text = _normalize_text(value)
    if not text:
        raise ValueError(message)
    return text


def _normalize_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_dt(value) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") and value else value


def _default_title(process: Process) -> str:
    if getattr(process, "code", None):
        return f"SIPOC - {process.code} - {process.name}"
    return f"SIPOC - {process.name}"
