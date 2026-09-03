from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from models import (
    Company,
    Indicator,
    MacroProcess,
    Process,
    ProcessActivityExecutionContract,
    ProcessActivityArtifactExecution,
    ProcessActivityArtifactLink,
    ProcessBpmnDiagram,
    ProcessInstance,
    ProcessInstanceExecution,
    ProcessRoutine,
    ProcessStep,
    Routine,
    RoutineCollaborator,
    db,
)
from services.process_book_service import (
    _compose_process_title,
    _extract_extension,
    _resolve_asset_url,
    build_process_book_context,
    _join_non_empty,
)
from services.process_bpmn_service import sanitize_svg_snapshot, serialize_flow_snapshot
from services.process_artifact_service import list_published_process_artifacts
from services.process_flow_copilot_service import build_process_flow_copilot_analysis
from services.process_resource_service import build_process_resources_bundle
from services.process_assignment_service import employee_assignment_execution_ids, is_execution_actionable
from utils.indicator_filters import (
    PROCESS_SOURCE_MODULES,
    indicator_supports_source_context,
)

KANBAN_STAGE_META = {
    "inbox": {"label": "Fora de escopo", "color": "#94a3b8"},
    "designing": {"label": "Desenho", "color": "#60a5fa"},
    "deploying": {"label": "Implantação", "color": "#2563eb"},
    "stabilizing": {"label": "Estabilização", "color": "#a855f7"},
    "stable": {"label": "Estável", "color": "#4f46e5"},
}

PERFORMANCE_META = {
    "critical": {"label": "Crítico", "color": "#ef4444"},
    "below": {"label": "Abaixo", "color": "#f59e0b"},
    "satisfactory": {"label": "Satisfatório", "color": "#10b981"},
}


class ProcessPortalAccessError(PermissionError):
    """Acesso negado ao processo no portal publicado."""


def build_process_portal_summary(
    company_id: int,
    *,
    current_employee_id: int | None,
    can_manage_all: bool,
) -> dict[str, Any]:
    company = Company.query.filter_by(id=company_id).first()
    if not company:
        raise ValueError("Empresa não encontrada.")

    processes = (
        Process.query.options(joinedload(Process.macro).joinedload(MacroProcess.area))
        .filter(Process.company_id == company_id)
        .order_by(Process.order_index.asc(), Process.id.asc())
        .all()
    )

    process_ids = [process.id for process in processes]
    my_active_activities = load_employee_active_activities(
        company_id,
        current_employee_id,
        process_ids=process_ids,
    )
    my_activity_counts = _count_activities_by_process(my_active_activities)
    accessible_process_ids = _resolve_accessible_process_ids(
        company_id=company_id,
        process_ids=process_ids,
        current_employee_id=current_employee_id,
        can_manage_all=can_manage_all,
    )

    pop_counts = _aggregate_counts(
        db.session.query(ProcessRoutine.process_id, func.count(ProcessRoutine.id))
        .filter(ProcessRoutine.company_id == company_id)
        .filter(ProcessRoutine.process_id.in_(process_ids or [0]))
        .group_by(ProcessRoutine.process_id)
        .all()
    )
    routine_counts = _aggregate_counts(
        db.session.query(Routine.process_id, func.count(Routine.id))
        .filter(Routine.company_id == company_id)
        .filter(Routine.process_id.in_(process_ids or [0]))
        .group_by(Routine.process_id)
        .all()
    )
    indicator_counts = _load_indicator_counts(company_id=company_id, process_ids=process_ids)
    spec_counts = _aggregate_counts(
        db.session.query(
            ProcessActivityExecutionContract.process_id,
            func.count(ProcessActivityExecutionContract.id),
        )
        .filter(ProcessActivityExecutionContract.company_id == company_id)
        .filter(ProcessActivityExecutionContract.is_active.is_(True))
        .filter(ProcessActivityExecutionContract.process_id.in_(process_ids or [0]))
        .group_by(ProcessActivityExecutionContract.process_id)
        .all()
    )
    published_diagram_ids = {
        row[0]
        for row in db.session.query(ProcessBpmnDiagram.process_id)
        .filter(ProcessBpmnDiagram.company_id == company_id)
        .filter(ProcessBpmnDiagram.status == "published")
        .filter(ProcessBpmnDiagram.process_id.in_(process_ids or [0]))
        .all()
    }
    video_process_ids = {
        row[0]
        for row in db.session.query(ProcessRoutine.process_id)
        .join(ProcessStep, ProcessStep.routine_id == ProcessRoutine.id)
        .filter(ProcessRoutine.company_id == company_id)
        .filter(ProcessRoutine.process_id.in_(process_ids or [0]))
        .filter(ProcessStep.video_path.isnot(None))
        .distinct()
        .all()
    }

    areas_map: dict[int, dict[str, Any]] = {}
    for process in processes:
        macro = getattr(process, "macro", None)
        area = getattr(macro, "area", None) if macro else None
        area_key = getattr(area, "id", 0) or 0
        if area_key not in areas_map:
            areas_map[area_key] = {
                "id": area_key,
                "name": getattr(area, "name", None) or "Sem área",
                "code": getattr(area, "code", None),
                "color": getattr(area, "color", None) or "#2563eb",
                "macros": {},
            }

        macros = areas_map[area_key]["macros"]
        macro_key = getattr(macro, "id", 0) or 0
        if macro_key not in macros:
            macros[macro_key] = {
                "id": macro_key,
                "name": getattr(macro, "name", None) or "Sem macroprocesso",
                "code": getattr(macro, "code", None),
                "owner": getattr(macro, "owner", None),
                "processes": [],
            }

        has_access = process.id in accessible_process_ids
        macros[macro_key]["processes"].append(
            {
                "id": process.id,
                "name": process.name,
                "code": process.code,
                "display_name": _compose_process_title(process.code, process.name, fallback=process.name),
                "has_access": has_access,
                "access_label": "Disponível" if has_access else "Sem vínculo operacional",
                "stage": _build_stage_meta(process.kanban_stage),
                "performance": _build_performance_meta(process.performance_level),
                "stats": {
                    "pop_count": pop_counts.get(process.id, 0),
                    "routine_count": routine_counts.get(process.id, 0),
                    "indicator_count": indicator_counts.get(process.id, 0),
                    "spec_count": spec_counts.get(process.id, 0),
                    "has_published_flow": process.id in published_diagram_ids,
                    "has_video": process.id in video_process_ids,
                    "my_active_activity_count": my_activity_counts.get(process.id, 0),
                },
            }
        )

    areas = []
    for area in sorted(areas_map.values(), key=lambda item: ((item.get("code") or ""), item.get("name") or "")):
        macros = list(area["macros"].values())
        macros.sort(key=lambda item: ((item.get("code") or ""), item.get("name") or ""))
        for macro in macros:
            macro["processes"].sort(key=lambda item: ((item.get("code") or ""), item.get("name") or ""))
        area["macros"] = macros
        areas.append(area)

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "client_code": getattr(company, "client_code", None),
        },
        "summary": {
            "total_processes": len(processes),
            "accessible_processes": len(accessible_process_ids),
            "published_flows": len(published_diagram_ids),
            "my_active_activity_count": len(my_active_activities),
        },
        "my_active_activities": my_active_activities,
        "areas": areas,
    }


def build_process_portal_process_detail(
    company_id: int,
    process_id: int,
    *,
    current_employee_id: int | None,
    can_manage_all: bool,
    request_root: str | None = None,
) -> dict[str, Any]:
    process = (
        Process.query.options(joinedload(Process.macro).joinedload(MacroProcess.area))
        .filter(Process.company_id == company_id, Process.id == process_id)
        .first()
    )
    if not process:
        raise ValueError("Processo não encontrado para a empresa ativa.")

    accessible_process_ids = _resolve_accessible_process_ids(
        company_id=company_id,
        process_ids=[process.id],
        current_employee_id=current_employee_id,
        can_manage_all=can_manage_all,
    )
    if process.id not in accessible_process_ids:
        raise ProcessPortalAccessError("Você não possui vínculo com este processo publicado.")

    context = build_process_book_context(
        process_id=process.id,
        company_id=company_id,
        request_root=request_root,
    )

    diagram = _get_latest_portal_diagram(company_id=company_id, process_id=process.id)
    flow_payload = serialize_flow_snapshot(diagram)
    flow_document_url = _resolve_asset_url(getattr(process, "flow_document", None), root_url=(request_root or "").rstrip("/"))

    contracts = (
        ProcessActivityExecutionContract.query.filter_by(
            company_id=company_id,
            process_id=process.id,
            is_active=True,
        )
        .order_by(
            ProcessActivityExecutionContract.bpmn_element_id.asc().nulls_last(),
            ProcessActivityExecutionContract.version.desc(),
            ProcessActivityExecutionContract.id.desc(),
        )
        .all()
    )
    contract_payload = [_serialize_contract(item) for item in contracts]

    flow_copilot = None
    try:
        flow_copilot = build_process_flow_copilot_analysis(company_id=company_id, process_id=process.id)
    except Exception:
        flow_copilot = None

    pop_activities = _load_portal_pop_activities(
        company_id=company_id,
        process_id=process.id,
        request_root=request_root,
    )
    operational_artifacts = list_published_process_artifacts(
        company_id,
        process.id,
        artifact_types=("form", "check"),
    )
    _attach_artifacts_to_pop_activities(pop_activities, operational_artifacts)
    pop_by_bpmn = _index_pop_activities_by_bpmn(company_id=company_id, process_id=process.id)
    pop_bindings = []
    pop_candidates = ((diagram.metadata_json or {}).get("pop_candidates") or []) if diagram else []
    for candidate in pop_candidates:
        element_id = str(candidate.get("code") or candidate.get("id") or "").strip()
        routine = pop_by_bpmn.get(element_id)
        pop_bindings.append(
            {
                "bpmn_element_id": element_id,
                "bpmn_element_name": candidate.get("name") or element_id,
                "routine_id": routine.get("id") if routine else None,
                "routine_code": routine.get("code") if routine else None,
                "routine_name": routine.get("name") if routine else None,
                "has_video": bool(routine and routine.get("has_video")),
            }
        )

    indicators = list(context.get("indicators") or [])
    routines = list(context.get("routines") or [])
    videos = _collect_video_entries(pop_activities)
    resources = build_process_resources_bundle(company_id, process.id)
    my_active_activities = load_employee_active_activities(
        company_id,
        current_employee_id,
        process_ids=[process.id],
    )

    macro = getattr(process, "macro", None)
    area = getattr(macro, "area", None) if macro else None
    return {
        "id": process.id,
        "company_id": process.company_id,
        "name": process.name,
        "code": process.code,
        "description": process.description,
        "responsible": process.responsible,
        "macro": {
            "id": getattr(macro, "id", None),
            "name": getattr(macro, "name", None),
            "code": getattr(macro, "code", None),
            "owner": getattr(macro, "owner", None),
        },
        "area": {
            "id": getattr(area, "id", None),
            "name": getattr(area, "name", None),
            "code": getattr(area, "code", None),
            "color": getattr(area, "color", None),
        },
        "stage": _build_stage_meta(process.kanban_stage),
        "performance": _build_performance_meta(process.performance_level),
        "flow": {
            "bpmn_flow": flow_payload,
            "flow_document_url": flow_document_url,
            "flow_document_extension": _extract_extension(getattr(process, "flow_document", None)),
            "book_url": f"/processes/{process.id}/book",
            "export_bpmn_url": f"/api/processes/{process.id}/bpmn-diagram/export?status=published",
        },
        "stats": {
            "pop_count": len(pop_activities),
            "routine_count": len(routines),
            "indicator_count": len(indicators),
            "spec_count": len(contract_payload),
            "video_count": len(videos),
            "resource_count": len(resources.get("links") or []),
            "form_count": sum(1 for item in operational_artifacts if item.get("artifact_type") == "form"),
            "check_count": sum(1 for item in operational_artifacts if item.get("artifact_type") == "check"),
            "my_active_activity_count": len(my_active_activities),
        },
        "pop_activities": pop_activities,
        "operational_artifacts": operational_artifacts,
        "routines": routines,
        "indicators": indicators,
        "resources": resources,
        "ai_specs": {
            "contracts": contract_payload,
            "flow_copilot_analysis": flow_copilot,
        },
        "videos": videos,
        "pop_bindings": pop_bindings,
        "my_active_activities": my_active_activities,
        "notes": process.notes,
    }


def load_employee_active_activities(
    company_id: int,
    employee_id: int | None,
    *,
    process_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Projecao unica do trabalho acionavel do colaborador no portal."""
    if not employee_id:
        return []
    execution_ids = employee_assignment_execution_ids(company_id, employee_id)
    if not execution_ids:
        return []

    query = (
        ProcessInstanceExecution.query.join(
            ProcessInstance,
            ProcessInstance.id == ProcessInstanceExecution.process_instance_id,
        )
        .filter(
            ProcessInstanceExecution.company_id == company_id,
            ProcessInstance.company_id == company_id,
            ProcessInstanceExecution.id.in_(execution_ids),
            ProcessInstanceExecution.status.in_(
                ["pending", "ready", "in_progress", "paused", "waiting_external", "waiting_human"]
            ),
        )
    )
    if process_ids is not None:
        query = query.filter(ProcessInstanceExecution.process_id.in_(process_ids or [-1]))
    executions = query.order_by(ProcessInstance.due_date.asc().nulls_last(), ProcessInstanceExecution.id.asc()).all()
    executions = [execution for execution in executions if is_execution_actionable(execution)]
    if not executions:
        return []

    execution_ids_list = [row.id for row in executions]
    instance_ids = sorted({row.process_instance_id for row in executions})
    artifact_rows = (
        ProcessActivityArtifactExecution.query.filter(
            ProcessActivityArtifactExecution.company_id == company_id,
            or_(
                ProcessActivityArtifactExecution.activity_execution_id.in_(execution_ids_list),
                and_(
                    ProcessActivityArtifactExecution.process_instance_id.in_(instance_ids),
                    ProcessActivityArtifactExecution.scope_key.like("process_instance:%"),
                ),
            ),
        )
        .order_by(ProcessActivityArtifactExecution.id.asc())
        .all()
    )
    artifacts_by_execution: dict[int, list[ProcessActivityArtifactExecution]] = defaultdict(list)
    shared_by_instance: dict[int, list[ProcessActivityArtifactExecution]] = defaultdict(list)
    for artifact in artifact_rows:
        artifacts_by_execution[int(artifact.activity_execution_id)].append(artifact)
        if str(artifact.scope_key or "").startswith("process_instance:"):
            shared_by_instance[int(artifact.process_instance_id)].append(artifact)

    definition_ids = sorted({int(row.artifact_definition_id) for row in artifact_rows})
    links = ProcessActivityArtifactLink.query.filter(
        ProcessActivityArtifactLink.company_id == company_id,
        ProcessActivityArtifactLink.artifact_definition_id.in_(definition_ids or [-1]),
        ProcessActivityArtifactLink.is_active.is_(True),
    ).all()
    links_by_activity = {
        (int(link.process_id), str(link.bpmn_element_id), int(link.artifact_definition_id)): link
        for link in links
    }

    payload = []
    for execution in executions:
        instance = execution.process_instance
        artifacts = list(artifacts_by_execution.get(int(execution.id), []))
        for shared_artifact in shared_by_instance.get(int(instance.id), []):
            current_link = links_by_activity.get(
                (int(execution.process_id), str(execution.bpmn_element_id), int(shared_artifact.artifact_definition_id))
            )
            if current_link and all(item.id != shared_artifact.id for item in artifacts):
                artifacts.append(shared_artifact)
        required_pending = 0
        document_items = []
        for artifact in artifacts:
            current_link = links_by_activity.get(
                (int(execution.process_id), str(execution.bpmn_element_id), int(artifact.artifact_definition_id))
            )
            link = current_link.to_dict(include_definition=False) if current_link else dict((artifact.definition_snapshot_json or {}).get("link") or {})
            phase = (((artifact.output_json or {}).get("_workflow") or {}).get("activity_phases") or {}).get(str(execution.id)) or {}
            artifact_status = phase.get("status") or artifact.status
            if link.get("is_required") and artifact_status not in {"completed", "skipped"}:
                required_pending += 1
            snapshot = artifact.definition_snapshot_json or {}
            document_items.append(
                {
                    "id": int(artifact.id),
                    "type": str(artifact.artifact_type),
                    "name": snapshot.get("name") or str(artifact.artifact_type).upper(),
                    "status": str(artifact_status),
                    "is_required": bool(link.get("is_required")),
                }
            )
        payload.append(
            {
                "execution_id": int(execution.id),
                "instance_id": int(instance.id),
                "instance_code": instance.instance_code,
                "instance_title": instance.title,
                "process_id": int(execution.process_id),
                "activity_id": execution.bpmn_element_id,
                "activity_name": execution.bpmn_element_name or execution.bpmn_element_id,
                "execution_mode": execution.execution_mode,
                "status": execution.status,
                "priority": instance.priority,
                "due_date": instance.due_date.isoformat() if instance.due_date else None,
                "artifact_types": sorted({str(item.artifact_type) for item in artifacts}),
                "documents": document_items,
                "required_artifacts_pending": required_pending,
                "execution_url": (
                    f"/my-work/process-instance/{instance.id}"
                    f"?execution_id={execution.id}&company_id={company_id}&from=process-portal"
                ),
            }
        )
    return payload


def _attach_artifacts_to_pop_activities(
    pop_activities: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> None:
    """Anexa referencias publicadas ao POP usando o elemento BPMN como fonte unica."""
    artifacts_by_element: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in artifacts:
        for link in artifact.get("activity_links") or []:
            element_id = str(link.get("bpmn_element_id") or "").strip()
            if not element_id:
                continue
            artifacts_by_element[element_id].append(
                {
                    **artifact,
                    "activity_link": link,
                    "is_required": bool(link.get("is_required")),
                    "completion_policy_json": link.get("completion_policy_json") or {},
                }
            )

    for activity in pop_activities:
        element_id = str(activity.get("bpmn_element_id") or "").strip()
        activity["artifacts"] = list(artifacts_by_element.get(element_id, []))


def _count_activities_by_process(activities: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for activity in activities:
        counts[int(activity["process_id"])] += 1
    return dict(counts)


def _aggregate_counts(rows: list[tuple[int | None, int]]) -> dict[int, int]:
    payload: dict[int, int] = {}
    for key, value in rows:
        if key is None:
            continue
        payload[int(key)] = int(value or 0)
    return payload


def _load_indicator_counts(*, company_id: int, process_ids: list[int]) -> dict[int, int]:
    if not process_ids:
        return {}

    payload: dict[int, int] = {}
    if indicator_supports_source_context():
        rows = (
            db.session.query(
                Indicator.source_id.label("process_id"),
                func.count(Indicator.id).label("total"),
            )
            .filter(Indicator.company_id == company_id)
            .filter(Indicator.is_active.is_(True))
            .filter(Indicator.source_module.in_(PROCESS_SOURCE_MODULES))
            .filter(Indicator.source_id.in_(process_ids))
            .group_by(Indicator.source_id)
            .all()
        )
        payload = _aggregate_counts([(row.process_id, row.total) for row in rows])
    direct_rows = (
        db.session.query(Indicator.process_id, func.count(Indicator.id))
        .filter(Indicator.company_id == company_id)
        .filter(Indicator.is_active.is_(True))
        .filter(Indicator.process_id.in_(process_ids))
        .group_by(Indicator.process_id)
        .all()
    )
    for process_id, total in direct_rows:
        if process_id is None:
            continue
        payload[int(process_id)] = payload.get(int(process_id), 0) + int(total or 0)
    return payload


def _resolve_accessible_process_ids(
    *,
    company_id: int,
    process_ids: list[int],
    current_employee_id: int | None,
    can_manage_all: bool,
) -> set[int]:
    if not process_ids:
        return set()
    if can_manage_all or not current_employee_id:
        return set(process_ids) if can_manage_all else set()

    accessible: set[int] = set(
        row[0]
        for row in db.session.query(Process.id)
        .filter(Process.company_id == company_id)
        .filter(Process.id.in_(process_ids))
        .filter(
            or_(
                Process.owner_employee_id == current_employee_id,
                Process.responsible_id == current_employee_id,
            )
        )
        .all()
    )
    accessible.update(
        row[0]
        for row in db.session.query(Routine.process_id)
        .join(RoutineCollaborator, RoutineCollaborator.routine_id == Routine.id)
        .filter(Routine.company_id == company_id)
        .filter(Routine.process_id.in_(process_ids))
        .filter(RoutineCollaborator.employee_id == current_employee_id)
        .distinct()
        .all()
        if row[0] is not None
    )
    accessible.update(
        row[0]
        for row in db.session.query(ProcessInstance.process_id)
        .filter(ProcessInstance.company_id == company_id)
        .filter(ProcessInstance.process_id.in_(process_ids))
        .filter(
            or_(
                ProcessInstance.owner_employee_id == current_employee_id,
                ProcessInstance.responsible_id == current_employee_id,
                ProcessInstance.executor_id == current_employee_id,
            )
        )
        .distinct()
        .all()
        if row[0] is not None
    )
    assigned_execution_ids = employee_assignment_execution_ids(company_id, current_employee_id)
    accessible.update(
        row[0]
        for row in db.session.query(ProcessInstanceExecution.process_id)
        .filter(ProcessInstanceExecution.company_id == company_id)
        .filter(ProcessInstanceExecution.process_id.in_(process_ids))
        .filter(ProcessInstanceExecution.id.in_(assigned_execution_ids or [-1]))
        .distinct()
        .all()
        if row[0] is not None
    )
    return accessible


def _build_stage_meta(value: str | None) -> dict[str, str]:
    key = str(value or "inbox").strip().lower()
    meta = KANBAN_STAGE_META.get(key, KANBAN_STAGE_META["inbox"])
    return {"key": key, "label": meta["label"], "color": meta["color"]}


def _build_performance_meta(value: str | None) -> dict[str, str]:
    key = str(value or "").strip().lower()
    meta = PERFORMANCE_META.get(key, {"label": "Não informado", "color": "#64748b"})
    return {"key": key, "label": meta["label"], "color": meta["color"]}


def _get_latest_portal_diagram(*, company_id: int, process_id: int) -> ProcessBpmnDiagram | None:
    published = (
        ProcessBpmnDiagram.query.filter_by(
            company_id=company_id,
            process_id=process_id,
            status="published",
        )
        .order_by(ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )
    if published:
        return published
    return (
        ProcessBpmnDiagram.query.filter_by(
            company_id=company_id,
            process_id=process_id,
            status="draft",
        )
        .order_by(ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )


def _serialize_contract(contract: ProcessActivityExecutionContract) -> dict[str, Any]:
    payload = contract.to_dict()
    payload["spec_summary"] = _summarize_contract_spec(payload)
    return payload


def _summarize_contract_spec(payload: dict[str, Any]) -> dict[str, Any]:
    ai_config = payload.get("ai_config_json") or {}
    mcp_config = payload.get("mcp_config_json") or {}
    ui_schema = payload.get("ui_schema_json") or {}
    return {
        "execution_mode": payload.get("execution_mode"),
        "interaction_mode": payload.get("interaction_mode"),
        "tool_source": ai_config.get("tool_source"),
        "instruction": ai_config.get("instruction"),
        "allowed_tools": ai_config.get("allowed_tools") or [],
        "route_name": payload.get("route_name"),
        "mcp_tool": mcp_config.get("tool_name") or mcp_config.get("server_name"),
        "open_in": ui_schema.get("open_in"),
    }


def _index_pop_activities_by_bpmn(*, company_id: int, process_id: int) -> dict[str, dict[str, Any]]:
    routines = (
        ProcessRoutine.query.filter(
            ProcessRoutine.company_id == company_id,
            ProcessRoutine.process_id == process_id,
            ProcessRoutine.bpmn_element_id.isnot(None),
            or_(ProcessRoutine.is_active.is_(True), ProcessRoutine.is_active.is_(None)),
        )
        .order_by(ProcessRoutine.order_index.asc(), ProcessRoutine.id.asc())
        .all()
    )
    if not routines:
        return {}

    routine_ids = [routine.id for routine in routines]
    video_routine_ids = {
        row[0]
        for row in db.session.query(ProcessStep.routine_id)
        .filter(ProcessStep.routine_id.in_(routine_ids))
        .filter(ProcessStep.video_path.isnot(None))
        .distinct()
        .all()
        if row[0] is not None
    }
    payload = {}
    for routine in routines:
        payload[str(routine.bpmn_element_id)] = {
            "id": routine.id,
            "code": routine.code,
            "name": routine.name,
            "has_video": routine.id in video_routine_ids,
        }
    return payload


def _collect_video_entries(pop_activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    for activity in pop_activities:
        for entry in activity.get("entries") or []:
            video_url = entry.get("video_url")
            if not video_url:
                continue
            videos.append(
                {
                    "activity_name": activity.get("name"),
                    "step_name": entry.get("name"),
                    "video_url": video_url,
                    "video_duration_seconds": entry.get("video_duration_seconds"),
                    "video_narration": entry.get("video_narration"),
                }
            )
    return videos


def _load_portal_pop_activities(
    *,
    company_id: int,
    process_id: int,
    request_root: str | None,
) -> list[dict[str, Any]]:
    root_url = (request_root or "").rstrip("/")
    routines = (
        ProcessRoutine.query.filter(
            ProcessRoutine.company_id == company_id,
            ProcessRoutine.process_id == process_id,
            or_(ProcessRoutine.is_active.is_(True), ProcessRoutine.is_active.is_(None)),
        )
        .order_by(ProcessRoutine.order_index.asc(), ProcessRoutine.id.asc())
        .all()
    )
    if not routines:
        return []

    routine_ids = [routine.id for routine in routines]
    steps = (
        ProcessStep.query.filter(ProcessStep.routine_id.in_(routine_ids))
        .order_by(ProcessStep.routine_id.asc(), ProcessStep.order_index.asc(), ProcessStep.id.asc())
        .all()
    )
    steps_by_routine: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for step in steps:
        steps_by_routine[int(step.routine_id)].append(
            {
                "id": step.id,
                "name": step.name,
                "description": step.description,
                "expected_result": step.expected_result,
                "layout": step.layout or "single",
                "image_url": _resolve_asset_url(step.image_path, root_url=root_url),
                "video_url": _resolve_asset_url(step.video_path, root_url=root_url),
                "video_duration_seconds": step.video_duration_seconds,
                "video_narration": step.video_narration,
                "text_content": _join_non_empty(
                    [
                        step.description,
                        f"Resultado esperado: {step.expected_result}" if step.expected_result else None,
                    ]
                ),
            }
        )

    payload = []
    for routine in routines:
        entries = steps_by_routine.get(routine.id, [])
        payload.append(
            {
                "id": routine.id,
                "code": routine.code or "-",
                "name": routine.name,
                "description": routine.description,
                "bpmn_element_id": routine.bpmn_element_id,
                "entries": entries,
            }
        )
    return payload
