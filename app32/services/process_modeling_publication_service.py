from __future__ import annotations

import hashlib
import json
from typing import Any

from models import (
    MacroProcess,
    Process,
    ProcessActivityArtifactDefinition,
    ProcessActivityArtifactLink,
    ProcessBpmnDiagram,
    ProcessRoutine,
    ProcessSipocItem,
    ProcessSipocRegulatoryItem,
    ProcessSipocSnapshot,
    ProcessStep,
    db,
)
from services.process_artifact_service import (
    build_definition_snapshot,
    create_artifact_definition,
    ensure_pop_artifact_for_routine,
    link_artifact_to_activity,
    publish_artifact_definition,
)
from services.process_bpmn_service import upsert_process_bpmn_diagram


class ProcessModelingPublicationError(ValueError):
    """Erro funcional da publicação aprovada de modelagem de processos."""


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ProcessModelingPublicationError(f"{field} é obrigatório.")
    return text


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _process(company_id: int, process_id: int) -> Process:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if process is None:
        raise ProcessModelingPublicationError("Processo não encontrado para este tenant.")
    return process


def _apply_process_profile(process: Process, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProcessModelingPublicationError("process_profile deve ser um objeto.")
    if payload.get("code"):
        process.code = _required_text(payload.get("code"), "code")
    if payload.get("name"):
        process.name = _required_text(payload.get("name"), "name")
    if "description" in payload:
        process.description = str(payload.get("description") or "").strip() or None
    if "responsible" in payload:
        process.responsible = str(payload.get("responsible") or "").strip() or None
    macro_owner = str(payload.get("macro_owner") or "").strip()
    if macro_owner:
        macro = MacroProcess.query.filter_by(
            id=process.macro_id,
            company_id=process.company_id,
        ).first()
        if macro is None:
            raise ProcessModelingPublicationError("Macroprocesso não encontrado para este tenant.")
        macro.owner = macro_owner
    db.session.commit()
    return {
        "id": process.id,
        "company_id": process.company_id,
        "code": process.code,
        "name": process.name,
        "responsible": process.responsible,
    }


def _publish_bpmn(process: Process, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProcessModelingPublicationError("bpmn deve ser um objeto.")
    bpmn_xml = payload.get("bpmn_xml")
    if not isinstance(bpmn_xml, str) or not bpmn_xml.strip():
        raise ProcessModelingPublicationError("bpmn_xml é obrigatório.")
    source_hash = hashlib.sha256(bpmn_xml.encode("utf-8")).hexdigest()
    declared_hash = str(payload.get("source_sha256") or "").strip()
    if declared_hash and declared_hash != source_hash:
        raise ProcessModelingPublicationError("Hash declarado do BPMN diverge do conteúdo.")

    current = (
        ProcessBpmnDiagram.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            status="published",
        )
        .order_by(ProcessBpmnDiagram.id.desc())
        .first()
    )
    current_hash = (
        ((current.metadata_json or {}).get("modeling_publication") or {}).get("source_sha256")
        if current
        else None
    )
    if current is not None and current_hash == source_hash:
        diagram = current
        operation = "noop"
    else:
        metadata = dict(payload.get("metadata_json") or {})
        metadata["modeling_publication"] = {
            "source_sha256": source_hash,
            "human_gate_confirmed": True,
        }
        diagram = upsert_process_bpmn_diagram(
            process=process,
            payload={
                "status": "published",
                "name": str(payload.get("name") or process.name).strip(),
                "bpmn_xml": bpmn_xml,
                "metadata_json": metadata,
            },
            user_id=None,
        )
        operation = "published"
    return {
        "operation": operation,
        "id": diagram.id,
        "version": diagram.version,
        "status": diagram.status,
        "source_sha256": source_hash,
    }


def _link_signature(definition: ProcessActivityArtifactDefinition) -> list[dict[str, Any]]:
    links = (
        definition.activity_links.filter_by(
            company_id=definition.company_id,
            process_id=definition.process_id,
            is_active=True,
        )
        .order_by(ProcessActivityArtifactLink.display_order, ProcessActivityArtifactLink.id)
        .all()
    )
    return [
        {
            "bpmn_element_id": link.bpmn_element_id,
            "is_required": bool(link.is_required),
            "completion_policy_json": link.completion_policy_json or {},
        }
        for link in links
    ]


def _publish_artifact(process: Process, payload: dict[str, Any]) -> dict[str, Any]:
    artifact_key = _required_text(payload.get("artifact_key"), "artifact_key")
    artifact_type = _required_text(payload.get("artifact_type"), "artifact_type")
    name = _required_text(payload.get("name"), "name do artefato")
    links = payload.get("activity_links") or []
    if not isinstance(links, list) or not links:
        raise ProcessModelingPublicationError("activity_links deve conter ao menos um vínculo.")

    desired_links = [
        {
            "bpmn_element_id": _required_text(item.get("bpmn_element_id"), "bpmn_element_id"),
            "is_required": bool(item.get("is_required", False)),
            "completion_policy_json": item.get("completion_policy_json") or {},
        }
        for item in links
    ]
    desired_definition = {
        "artifact_type": artifact_type,
        "name": name,
        "description": str(payload.get("description") or "").strip() or None,
        "execution_scope": str(payload.get("execution_scope") or "activity").strip(),
        "configuration_json": payload.get("configuration_json") or {},
    }
    published = (
        ProcessActivityArtifactDefinition.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            artifact_key=artifact_key,
            status="published",
        )
        .order_by(
            ProcessActivityArtifactDefinition.version.desc(),
            ProcessActivityArtifactDefinition.id.desc(),
        )
        .all()
    )
    definition = next(
        (
            row
            for row in published
            if _canonical(
                {
                    "artifact_type": row.artifact_type,
                    "name": row.name,
                    "description": row.description,
                    "execution_scope": row.execution_scope,
                    "configuration_json": row.configuration_json or {},
                }
            )
            == _canonical(desired_definition)
            and _canonical(_link_signature(row)) == _canonical(desired_links)
        ),
        None,
    )
    operation = "noop"
    if definition is None:
        next_version = max([row.version for row in published] + [0]) + 1
        definition = create_artifact_definition(
            process.company_id,
            process.id,
            {
                "artifact_key": artifact_key,
                "artifact_type": artifact_type,
                "name": name,
                "description": desired_definition["description"],
                "version": next_version,
                "status": "draft",
                "execution_scope": desired_definition["execution_scope"],
                "configuration_json": desired_definition["configuration_json"],
            },
            commit=False,
        )
        for display_order, link_payload in enumerate(desired_links, start=1):
            link_artifact_to_activity(
                process.company_id,
                process.id,
                definition.id,
                {**link_payload, "display_order": display_order, "is_active": True},
                commit=False,
            )
        db.session.commit()
        definition = publish_artifact_definition(process.company_id, definition.id)
        operation = "published"

    for old in published:
        if old.id == definition.id:
            continue
        old.status = "archived"
        for link in old.activity_links.all():
            link.is_active = False
    db.session.commit()
    snapshot = build_definition_snapshot(definition)
    return {
        "operation": operation,
        "id": definition.id,
        "artifact_key": definition.artifact_key,
        "artifact_type": definition.artifact_type,
        "version": definition.version,
        "status": definition.status,
        "execution_scope": definition.execution_scope,
        "activity_links": snapshot.get("activity_links") or [],
    }


def _publish_pop(process: Process, payload: dict[str, Any]) -> dict[str, Any]:
    code = _required_text(payload.get("code"), "code do POP")
    activity_ids = payload.get("activity_ids") or []
    steps = payload.get("steps") or []
    if not isinstance(activity_ids, list) or not activity_ids:
        raise ProcessModelingPublicationError("activity_ids do POP é obrigatório.")
    if not isinstance(steps, list) or not steps:
        raise ProcessModelingPublicationError("steps do POP é obrigatório.")
    primary_id = _required_text(payload.get("primary_bpmn_element_id") or activity_ids[0], "primary_bpmn_element_id")

    routine = ProcessRoutine.query.filter_by(
        company_id=process.company_id,
        process_id=process.id,
        code=code,
    ).first()
    operation = "updated" if routine else "created"
    if routine is None:
        routine = ProcessRoutine(
            company_id=process.company_id,
            process_id=process.id,
            code=code,
            name=_required_text(payload.get("name"), "name do POP"),
            description=str(payload.get("description") or "").strip() or None,
            bpmn_element_id=primary_id,
            bpmn_element_type=str(payload.get("bpmn_element_type") or "bpmn:Task"),
            bpmn_data_objects=payload.get("bpmn_data_objects") or [],
            is_active=True,
        )
        db.session.add(routine)
        db.session.flush()
    routine.name = _required_text(payload.get("name"), "name do POP")
    routine.description = str(payload.get("description") or "").strip() or None
    routine.bpmn_element_id = primary_id
    routine.bpmn_element_type = str(payload.get("bpmn_element_type") or "bpmn:Task")
    routine.bpmn_data_objects = payload.get("bpmn_data_objects") or []
    routine.is_active = True

    existing = {step.order_index: step for step in routine.steps.all()}
    desired_orders: set[int] = set()
    for fallback_order, step_payload in enumerate(steps, start=1):
        order_index = int(step_payload.get("order_index") or fallback_order)
        desired_orders.add(order_index)
        step = existing.get(order_index)
        if step is None:
            step = ProcessStep(routine_id=routine.id, order_index=order_index)
            db.session.add(step)
        step.name = _required_text(step_payload.get("name"), "name do passo")
        step.description = str(step_payload.get("description") or "").strip() or None
        step.expected_result = str(step_payload.get("expected_result") or "").strip() or None
    for order_index, step in existing.items():
        if order_index not in desired_orders:
            db.session.delete(step)
    db.session.flush()

    definition, _, _ = ensure_pop_artifact_for_routine(routine, commit=False)
    desired_activity_ids = {_required_text(value, "activity_id do POP") for value in activity_ids}
    for display_order, activity_id in enumerate(activity_ids, start=1):
        link_artifact_to_activity(
            process.company_id,
            process.id,
            definition.id,
            {
                "bpmn_element_id": activity_id,
                "display_order": display_order,
                "is_required": False,
                "is_active": True,
                "completion_policy_json": {
                    "mode": "available",
                    "acknowledgement_required": False,
                },
            },
            commit=False,
        )
    for link in definition.activity_links.all():
        if link.bpmn_element_id not in desired_activity_ids:
            link.is_active = False
    db.session.commit()
    return {
        "operation": operation,
        "routine_id": routine.id,
        "definition_id": definition.id,
        "status": definition.status,
        "steps": routine.steps.count(),
        "activity_ids": sorted(desired_activity_ids),
    }


def publish_approved_process_modeling_package(
    *,
    company_id: int,
    process_id: int,
    package: dict[str, Any],
    human_gate_confirmed: bool,
) -> dict[str, Any]:
    """Materializa no APP32 um pacote aprovado pelo fluxo Squad Cliente -> Squad Versus."""
    if not human_gate_confirmed:
        raise ProcessModelingPublicationError("A aprovação humana explícita é obrigatória.")
    if not isinstance(package, dict):
        raise ProcessModelingPublicationError("package deve ser um objeto.")
    process = _process(int(company_id), int(process_id))

    profile_result = _apply_process_profile(process, package.get("process_profile") or {})
    bpmn_result = _publish_bpmn(process, package.get("bpmn") or {})
    pop_result = _publish_pop(process, package.get("pop") or {}) if package.get("pop") else None
    artifact_results = [
        _publish_artifact(process, artifact)
        for artifact in (package.get("artifacts") or [])
    ]
    return {
        "company_id": process.company_id,
        "process_id": process.id,
        "process": profile_result,
        "bpmn": bpmn_result,
        "pop": pop_result,
        "artifacts": artifact_results,
    }


def get_process_modeling_package(
    *,
    company_id: int,
    process_id: int,
    diagram_status: str = "published",
    include_bpmn_xml: bool = True,
) -> dict[str, Any]:
    """Relê o pacote vigente de modelagem sem atravessar o tenant informado."""
    process = _process(int(company_id), int(process_id))
    status = str(diagram_status or "published").strip().lower()
    if status not in {"draft", "published", "archived"}:
        raise ProcessModelingPublicationError("diagram_status deve ser draft, published ou archived.")

    macro = MacroProcess.query.filter_by(
        id=process.macro_id,
        company_id=process.company_id,
    ).first()
    diagram = (
        ProcessBpmnDiagram.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            status=status,
        )
        .order_by(ProcessBpmnDiagram.version.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )
    sipoc = (
        ProcessSipocSnapshot.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            status="published",
        )
        .order_by(ProcessSipocSnapshot.version.desc(), ProcessSipocSnapshot.id.desc())
        .first()
    )

    sipoc_payload = None
    if sipoc is not None:
        items = (
            ProcessSipocItem.query.filter_by(
                company_id=process.company_id,
                sipoc_snapshot_id=sipoc.id,
            )
            .order_by(ProcessSipocItem.lane, ProcessSipocItem.order_index, ProcessSipocItem.id)
            .all()
        )
        regulations = (
            ProcessSipocRegulatoryItem.query.filter_by(
                company_id=process.company_id,
                sipoc_snapshot_id=sipoc.id,
            )
            .order_by(ProcessSipocRegulatoryItem.id)
            .all()
        )
        sipoc_payload = {
            "id": sipoc.id,
            "version": sipoc.version,
            "status": sipoc.status,
            "title": sipoc.title,
            "objective": sipoc.objective,
            "start_boundary": sipoc.start_boundary,
            "end_boundary": sipoc.end_boundary,
            "trigger_event": sipoc.trigger_event,
            "customer_requirements": sipoc.customer_requirements,
            "constraints_notes": sipoc.constraints_notes,
            "measures_notes": sipoc.measures_notes,
            "risks_notes": sipoc.risks_notes,
            "notes": sipoc.notes,
            "items": [
                {
                    "id": item.id,
                    "lane": item.lane,
                    "title": item.title,
                    "description": item.description,
                    "order_index": item.order_index,
                    "source_type": item.source_type,
                    "source_ref": item.source_ref,
                    "is_critical": bool(item.is_critical),
                }
                for item in items
            ],
            "regulatory_items": [
                {
                    "id": item.id,
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
                }
                for item in regulations
            ],
        }

    routines = (
        ProcessRoutine.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            is_active=True,
        )
        .order_by(ProcessRoutine.order_index, ProcessRoutine.id)
        .all()
    )
    definitions = (
        ProcessActivityArtifactDefinition.query.filter_by(
            company_id=process.company_id,
            process_id=process.id,
            status="published",
        )
        .order_by(
            ProcessActivityArtifactDefinition.artifact_type,
            ProcessActivityArtifactDefinition.artifact_key,
            ProcessActivityArtifactDefinition.version.desc(),
            ProcessActivityArtifactDefinition.id.desc(),
        )
        .all()
    )
    artifact_payloads = []
    for definition in definitions:
        payload = definition.to_dict()
        payload["activity_links"] = _link_signature(definition)
        artifact_payloads.append(payload)

    diagram_payload = None
    if diagram is not None:
        diagram_payload = {
            "id": diagram.id,
            "version": diagram.version,
            "status": diagram.status,
            "name": diagram.name,
            "metadata_json": diagram.metadata_json or {},
            "published_at": _iso(diagram.published_at),
            "updated_at": _iso(diagram.updated_at),
        }
        if include_bpmn_xml:
            diagram_payload["bpmn_xml"] = diagram.bpmn_xml

    return {
        "company_id": process.company_id,
        "process_id": process.id,
        "process": {
            "id": process.id,
            "code": process.code,
            "name": process.name,
            "description": process.description,
            "responsible": process.responsible,
            "responsible_id": process.responsible_id,
            "owner_employee_id": process.owner_employee_id,
            "kanban_stage": process.kanban_stage,
            "structuring_level": process.structuring_level,
            "performance_level": process.performance_level,
            "notes": process.notes,
            "is_active": bool(process.is_active),
        },
        "macro_process": (
            {
                "id": macro.id,
                "area_id": macro.area_id,
                "code": macro.code,
                "name": macro.name,
                "description": macro.description,
                "owner": macro.owner,
            }
            if macro is not None
            else None
        ),
        "sipoc": sipoc_payload,
        "bpmn": diagram_payload,
        "pops": [
            {
                "routine_id": routine.id,
                "code": routine.code,
                "name": routine.name,
                "description": routine.description,
                "bpmn_element_id": routine.bpmn_element_id,
                "bpmn_element_type": routine.bpmn_element_type,
                "bpmn_data_objects": routine.bpmn_data_objects or [],
                "steps": [
                    {
                        "id": step.id,
                        "order_index": step.order_index,
                        "name": step.name,
                        "description": step.description,
                        "expected_result": step.expected_result,
                    }
                    for step in routine.steps.order_by(ProcessStep.order_index, ProcessStep.id).all()
                ],
            }
            for routine in routines
        ],
        "artifacts": artifact_payloads,
    }


__all__ = [
    "ProcessModelingPublicationError",
    "get_process_modeling_package",
    "publish_approved_process_modeling_package",
]
