from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func

from models import (
    Process,
    ProcessPortalPublication,
    ProcessPortalPublicationGrant,
    db,
)


VALID_PUBLICATION_STATUSES = {"draft", "published", "archived"}
VALID_VISIBILITY_SCOPES = {"company", "linked_process", "restricted"}
VALID_GRANT_SCOPES = {"company", "user", "employee", "process", "activity"}


def get_latest_publication(*, company_id: int, process_id: int, status: str = "published") -> ProcessPortalPublication | None:
    query = ProcessPortalPublication.query.filter_by(company_id=company_id, process_id=process_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(
        ProcessPortalPublication.publication_version.desc(),
        ProcessPortalPublication.id.desc(),
    ).first()


def list_publications(*, company_id: int, process_id: int) -> list[ProcessPortalPublication]:
    return (
        ProcessPortalPublication.query.filter_by(company_id=company_id, process_id=process_id)
        .order_by(ProcessPortalPublication.publication_version.desc(), ProcessPortalPublication.id.desc())
        .all()
    )


def publish_process_portal(
    *,
    process: Process,
    snapshot_payload: dict[str, Any],
    actor_user_id: int | None,
    visibility_scope: str = "linked_process",
    title: str | None = None,
    summary: str | None = None,
    source_bpmn_diagram_id: int | None = None,
    grants_payload: list[dict[str, Any]] | None = None,
) -> ProcessPortalPublication:
    if not isinstance(snapshot_payload, dict) or not snapshot_payload:
        raise ValueError("Snapshot de publicação inválido.")

    visibility_scope = str(visibility_scope or "linked_process").strip().lower()
    if visibility_scope not in VALID_VISIBILITY_SCOPES:
        raise ValueError("Escopo de visibilidade inválido.")

    next_version = (
        db.session.query(func.max(ProcessPortalPublication.publication_version))
        .filter_by(company_id=process.company_id, process_id=process.id)
        .scalar()
        or 0
    ) + 1

    (
        ProcessPortalPublication.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            status="published",
        )
        .update({"status": "archived"}, synchronize_session=False)
    )

    publication = ProcessPortalPublication(
        company_id=process.company_id,
        process_id=process.id,
        source_bpmn_diagram_id=source_bpmn_diagram_id,
        publication_version=next_version,
        status="published",
        visibility_scope=visibility_scope,
        title=(title or snapshot_payload.get("name") or process.name or f"Processo {process.id}").strip(),
        slug=_build_slug(process=process, version=next_version),
        summary=(summary or snapshot_payload.get("description") or process.description or "").strip() or None,
        content_snapshot_json=snapshot_payload,
        published_by_user_id=actor_user_id,
        published_at=datetime.utcnow(),
    )
    db.session.add(publication)
    db.session.flush()

    for item in grants_payload or []:
        normalized = _normalize_grant_payload(item, publication=publication)
        if normalized:
            db.session.add(ProcessPortalPublicationGrant(**normalized))

    db.session.commit()
    return publication


def _build_slug(*, process: Process, version: int) -> str:
    base = (getattr(process, "code", None) or getattr(process, "name", None) or f"processo-{process.id}").strip().lower()
    safe = "".join(ch if ch.isalnum() else "-" for ch in base)
    while "--" in safe:
        safe = safe.replace("--", "-")
    safe = safe.strip("-") or f"processo-{process.id}"
    return f"{safe}-v{version}"


def _normalize_grant_payload(item: dict[str, Any], *, publication: ProcessPortalPublication) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    grant_scope = str(item.get("grant_scope") or "").strip().lower()
    if grant_scope not in VALID_GRANT_SCOPES:
        return None
    payload = {
        "company_id": publication.company_id,
        "publication_id": publication.id,
        "grant_scope": grant_scope,
        "user_id": item.get("user_id"),
        "employee_id": item.get("employee_id"),
        "process_id": item.get("process_id"),
        "process_routine_id": item.get("process_routine_id"),
        "bpmn_element_id": item.get("bpmn_element_id"),
        "can_view": bool(item.get("can_view", True)),
    }
    return payload
