from __future__ import annotations

from datetime import datetime
from typing import Any

from models import ProcessBpmnDiagram, ProcessInstance, ProcessInstanceExecution, ProcessRoutine, db


INSTANCE_ALLOWED_STATUSES = {
    "pending",
    "in_progress",
    "paused",
    "waiting_external",
    "completed",
    "failed",
    "cancelled",
    "overdue",
}

EXECUTION_ALLOWED_STATUSES = {
    "pending",
    "ready",
    "in_progress",
    "paused",
    "waiting_external",
    "completed",
    "failed",
    "skipped",
}


def get_published_diagram_for_process(*, process_id: int, company_id: int) -> ProcessBpmnDiagram | None:
    return (
        ProcessBpmnDiagram.query
        .filter_by(process_id=process_id, company_id=company_id, status="published")
        .order_by(ProcessBpmnDiagram.version.desc(), ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )


def resolve_initial_bpmn_element_id(*, process_id: int, company_id: int) -> str | None:
    first_bound_routine = (
        ProcessRoutine.query
        .filter_by(process_id=process_id, company_id=company_id, is_active=True)
        .filter(ProcessRoutine.bpmn_element_id.isnot(None))
        .order_by(ProcessRoutine.order_index.asc(), ProcessRoutine.id.asc())
        .first()
    )
    if first_bound_routine and first_bound_routine.bpmn_element_id:
        return str(first_bound_routine.bpmn_element_id)
    return None


def apply_runtime_defaults(instance: ProcessInstance) -> ProcessInstance:
    if not instance:
        return instance

    if not instance.process_bpmn_diagram_id:
        diagram = get_published_diagram_for_process(
            process_id=instance.process_id,
            company_id=instance.company_id,
        )
        if diagram:
            instance.process_bpmn_diagram_id = diagram.id
            instance.process_version = diagram.version

    if not instance.current_bpmn_element_id:
        instance.current_bpmn_element_id = resolve_initial_bpmn_element_id(
            process_id=instance.process_id,
            company_id=instance.company_id,
        )

    if instance.status == "in_progress" and not instance.started_at:
        instance.started_at = datetime.utcnow()

    if instance.status == "completed" and not instance.completed_at:
        instance.completed_at = datetime.utcnow()
    return instance


def validate_instance_status(status: str | None) -> str:
    normalized = str(status or "pending").strip().lower()
    if normalized not in INSTANCE_ALLOWED_STATUSES:
        raise ValueError("Status da instância BPMN/BPMS inválido.")
    return normalized


def validate_execution_status(status: str | None) -> str:
    normalized = str(status or "pending").strip().lower()
    if normalized not in EXECUTION_ALLOWED_STATUSES:
        raise ValueError("Status da execução da atividade inválido.")
    return normalized


def pause_instance(*, instance: ProcessInstance, reason: str | None = None) -> ProcessInstance:
    instance.status = "paused"
    instance.paused_at = datetime.utcnow()
    if reason is not None:
        instance.pause_reason = str(reason).strip() or None
    db.session.flush()
    return instance


def resume_instance(*, instance: ProcessInstance) -> ProcessInstance:
    instance.status = "in_progress"
    if not instance.started_at:
        instance.started_at = datetime.utcnow()
    instance.paused_at = None
    instance.pause_reason = None
    db.session.flush()
    return instance


def build_runtime_overlay(instance: ProcessInstance) -> dict[str, Any]:
    executions = (
        ProcessInstanceExecution.query
        .filter_by(process_instance_id=instance.id, company_id=instance.company_id)
        .order_by(ProcessInstanceExecution.created_at.asc(), ProcessInstanceExecution.id.asc())
        .all()
    )
    elements = [execution.to_dict() for execution in executions]

    return {
        "instance_id": instance.id,
        "process_id": instance.process_id,
        "company_id": instance.company_id,
        "process_bpmn_diagram_id": instance.process_bpmn_diagram_id,
        "process_version": instance.process_version,
        "status": instance.status,
        "current_bpmn_element_id": instance.current_bpmn_element_id,
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "paused_at": instance.paused_at.isoformat() if instance.paused_at else None,
        "pause_reason": instance.pause_reason,
        "elements": elements,
    }


def build_runtime_payload(instance: ProcessInstance) -> dict[str, Any]:
    diagram = None
    if instance.process_bpmn_diagram_id:
        diagram = (
            ProcessBpmnDiagram.query
            .filter_by(id=instance.process_bpmn_diagram_id, company_id=instance.company_id)
            .first()
        )
    if not diagram:
        diagram = get_published_diagram_for_process(
            process_id=instance.process_id,
            company_id=instance.company_id,
        )

    return {
        "instance": instance.to_dict(),
        "diagram": {
            "id": diagram.id if diagram else None,
            "version": diagram.version if diagram else None,
            "status": diagram.status if diagram else None,
            "bpmn_xml": diagram.bpmn_xml if diagram else None,
            "svg_snapshot": diagram.svg_snapshot if diagram else None,
        },
        "overlay": build_runtime_overlay(instance),
        "timeline": build_instance_timeline(instance),
    }


def build_instance_timeline(instance: ProcessInstance) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    if instance.started_at:
        timeline.append({
            "kind": "instance_started",
            "timestamp": instance.started_at.isoformat(),
            "label": "Instância iniciada",
        })
    if instance.paused_at:
        timeline.append({
            "kind": "instance_paused",
            "timestamp": instance.paused_at.isoformat(),
            "label": "Instância pausada",
            "details": {"reason": instance.pause_reason},
        })
    for execution in (
        ProcessInstanceExecution.query
        .filter_by(process_instance_id=instance.id, company_id=instance.company_id)
        .order_by(ProcessInstanceExecution.created_at.asc(), ProcessInstanceExecution.id.asc())
        .all()
    ):
        if execution.started_at:
            timeline.append({
                "kind": "activity_started",
                "timestamp": execution.started_at.isoformat(),
                "label": execution.bpmn_element_name or execution.bpmn_element_id,
                "details": {
                    "execution_id": execution.id,
                    "status": execution.status,
                    "execution_mode": execution.execution_mode,
                },
            })
        if execution.completed_at:
            timeline.append({
                "kind": "activity_completed",
                "timestamp": execution.completed_at.isoformat(),
                "label": execution.bpmn_element_name or execution.bpmn_element_id,
                "details": {
                    "execution_id": execution.id,
                    "status": execution.status,
                    "execution_mode": execution.execution_mode,
                },
            })
    if instance.completed_at:
        timeline.append({
            "kind": "instance_completed",
            "timestamp": instance.completed_at.isoformat(),
            "label": "Instância concluída",
        })
    return sorted(timeline, key=lambda item: item.get("timestamp") or "")
