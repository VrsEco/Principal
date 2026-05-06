from __future__ import annotations

from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from models import ProcessBpmnDiagram, ProcessInstance, ProcessInstanceExecution, ProcessRoutine, db
from services.process_ai_execution_service import normalize_ai_contract_config, summarize_ai_contract_config
from services.process_execution_contract_service import resolve_activity_execution_contract


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

EXECUTION_MODE_LABELS = {
    "manual_external": "Controle manual externo",
    "human_task": "Tarefa humana no APP",
    "automatic": "Execução automática",
    "external_rest": "Integração REST",
    "external_mcp": "Integração MCP",
    "ai_task": "Atividade executada por IA",
    "ai_decision": "Decisão assistida por IA",
}

CONTRACT_CAPABILITY_TAB_MAP = {
    "contracts.customer.manage": "cliente",
    "contracts.party.manage": "cliente",
    "contracts.items.manage": "itens",
    "contracts.billing.manage": "faturamento",
    "contracts.schedule.manage": "periodicidade",
    "contracts.fiscal.manage": "fiscal",
    "contracts.notes.manage": "observacoes",
    "contracts.validation.manage": "validar",
    "contracts.pdf.manage": "gerar_pdf",
    "contracts.signed.manage": "contrato_assinado",
    "contracts.documents.manage": "documentos",
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

    current_activity = build_current_activity_payload(instance=instance, diagram=diagram)

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
        "current_activity": current_activity,
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


def build_current_activity_payload(
    *,
    instance: ProcessInstance,
    diagram: ProcessBpmnDiagram | None = None,
) -> dict[str, Any]:
    current_element_id = getattr(instance, "current_bpmn_element_id", None)
    if not diagram and getattr(instance, "process_bpmn_diagram_id", None):
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

    executions = (
        ProcessInstanceExecution.query
        .filter_by(process_instance_id=instance.id, company_id=instance.company_id)
        .order_by(ProcessInstanceExecution.updated_at.desc(), ProcessInstanceExecution.id.desc())
        .all()
    )
    current_execution = None
    if current_element_id:
        current_execution = next((item for item in executions if item.bpmn_element_id == current_element_id), None)
    if not current_execution:
        current_execution = next((item for item in executions if item.status == "in_progress"), None)

    routine = None
    if current_element_id:
        routine = (
            ProcessRoutine.query
            .filter_by(
                company_id=instance.company_id,
                process_id=instance.process_id,
                bpmn_element_id=current_element_id,
                is_active=True,
            )
            .order_by(ProcessRoutine.order_index.asc(), ProcessRoutine.id.asc())
            .first()
        )

    contract = resolve_activity_execution_contract(
        company_id=instance.company_id,
        process_id=instance.process_id,
        bpmn_element_id=current_element_id,
        process_routine_id=getattr(routine, "id", None),
    )
    navigation = _build_diagram_navigation(diagram.bpmn_xml if diagram else None, current_element_id)
    action = _build_current_activity_action(instance, contract, current_execution, current_element_id)

    return {
        "element_id": current_element_id,
        "element_name": (
            getattr(current_execution, "bpmn_element_name", None)
            or getattr(routine, "name", None)
            or action.get("element_name")
            or current_element_id
        ),
        "element_type": (
            getattr(current_execution, "bpmn_element_type", None)
            or getattr(routine, "bpmn_element_type", None)
            or action.get("element_type")
        ),
        "status": getattr(current_execution, "status", None) or getattr(instance, "status", None) or "pending",
        "execution": current_execution.to_dict() if current_execution else None,
        "routine": {
            "id": routine.id,
            "name": routine.name,
            "description": routine.description,
            "bpmn_element_id": routine.bpmn_element_id,
            "bpmn_element_type": routine.bpmn_element_type,
        } if routine else None,
        "contract": contract.to_dict() if contract else None,
        "action": action,
        "next_candidates": navigation.get("next_candidates", []),
    }


def _build_current_activity_action(
    instance: ProcessInstance,
    contract,
    execution: ProcessInstanceExecution | None,
    element_id: str | None,
) -> dict[str, Any]:
    execution_mode = (
        getattr(execution, "execution_mode", None)
        or getattr(contract, "execution_mode", None)
        or "human_task"
    )
    capability_key = getattr(execution, "capability_key", None) or getattr(contract, "capability_key", None)
    route_name = getattr(contract, "route_name", None)
    ui_schema = dict(getattr(contract, "ui_schema_json", None) or {})
    rest_config = dict(getattr(contract, "rest_config_json", None) or {})
    mcp_config = dict(getattr(contract, "mcp_config_json", None) or {})
    ai_config = normalize_ai_contract_config(
        getattr(contract, "ai_config_json", None),
        execution_mode=execution_mode,
    )
    internal_url = _resolve_internal_action_url(instance, contract, execution, ui_schema)
    external_url = _resolve_external_action_url(instance, contract, ui_schema, rest_config, mcp_config)

    action_label = {
        "human_task": "Abrir tela operacional",
        "manual_external": "Registrar execução externa",
        "automatic": "Executar automaticamente",
        "external_rest": "Executar integração REST",
        "external_mcp": "Executar integração MCP",
        "ai_task": "Executar atividade com IA",
        "ai_decision": "Executar decisão com IA",
    }.get(execution_mode, "Executar atividade")

    instruction = {
        "human_task": "Abra a tela operacional, registre a execução e conclua a atividade na shell.",
        "manual_external": "Use esta shell para controlar a etapa feita fora do APP, com início, conclusão e observações.",
        "automatic": "A atividade está preparada para automação interna conforme o contrato BPMS.",
        "external_rest": "A atividade usa uma integração REST configurada no contrato da activity.",
        "external_mcp": "A atividade usa uma integração MCP configurada no contrato da activity.",
        "ai_task": "A atividade usa a esteira de IA do APP32 com instrução estruturada, contexto runtime e fallback governado.",
        "ai_decision": "A decisão usa a esteira de IA do APP32 com opções fechadas, confiança mínima e fallback governado.",
    }.get(execution_mode, "Controle a execução desta atividade pela shell.")

    return {
        "execution_mode": execution_mode,
        "execution_mode_label": EXECUTION_MODE_LABELS.get(execution_mode, execution_mode),
        "capability_key": capability_key,
        "route_name": route_name,
        "interaction_mode": getattr(contract, "interaction_mode", None),
        "handler_key": getattr(contract, "auto_service_key", None) or getattr(execution, "handler_key", None),
        "requires_human_gate": bool(getattr(contract, "requires_human_gate", False)),
        "allows_pause": bool(getattr(contract, "allows_pause", True)) if contract else True,
        "allows_retry": bool(getattr(contract, "allows_retry", True)) if contract else True,
        "sla_minutes": getattr(contract, "sla_minutes", None),
        "ai_config": ai_config,
        "ai_summary": summarize_ai_contract_config(ai_config) if ai_config else {},
        "ai_enabled": execution_mode in {"ai_task", "ai_decision"},
        "internal_url": internal_url,
        "external_url": external_url,
        "action_label": action_label,
        "instruction": instruction,
        "can_start": bool(element_id) and execution is None,
        "can_mark_waiting": execution is not None and execution.status not in {"completed", "failed", "waiting_external"},
        "can_complete": execution is not None and execution.status != "completed",
        "can_fail": execution is not None and execution.status != "failed",
    }


def _resolve_internal_action_url(
    instance: ProcessInstance,
    contract,
    execution: ProcessInstanceExecution | None,
    ui_schema: dict[str, Any],
) -> str | None:
    company_id = getattr(instance, "company_id", None)
    context = _build_runtime_context(instance, execution)
    direct_template = (
        ui_schema.get("url_template")
        or ui_schema.get("internal_url")
        or getattr(contract, "route_name", None)
    )
    if direct_template and str(direct_template).strip().startswith("/"):
        return _format_runtime_url_template(str(direct_template), context)

    contract_business_id = context.get("contract_id")
    tab_key = ui_schema.get("tab") or CONTRACT_CAPABILITY_TAB_MAP.get(str(getattr(contract, "capability_key", "") or "").strip())
    if company_id and contract_business_id and tab_key:
        return f"/contracts/{contract_business_id}?company_id={company_id}&tab={tab_key}"
    return None


def _resolve_external_action_url(
    instance: ProcessInstance,
    contract,
    ui_schema: dict[str, Any],
    rest_config: dict[str, Any],
    mcp_config: dict[str, Any],
) -> str | None:
    context = _build_runtime_context(instance, None)
    for value in (
        ui_schema.get("external_url"),
        rest_config.get("url"),
        mcp_config.get("url"),
    ):
        text = str(value or "").strip()
        if not text:
            continue
        if text.startswith("http://") or text.startswith("https://"):
            return _format_runtime_url_template(text, context)
    return None


def _build_runtime_context(instance: ProcessInstance, execution: ProcessInstanceExecution | None) -> dict[str, Any]:
    runtime_context = dict(getattr(instance, "runtime_context_json", None) or {})
    payload = {
        "company_id": instance.company_id,
        "process_id": instance.process_id,
        "instance_id": instance.id,
        "current_bpmn_element_id": getattr(instance, "current_bpmn_element_id", None),
        "contract_id": runtime_context.get("contract_id"),
    }
    if execution:
        payload["execution_id"] = execution.id
    for key, value in runtime_context.items():
        payload.setdefault(key, value)
    return payload


def _format_runtime_url_template(template: str, context: dict[str, Any]) -> str:
    output = str(template or "").strip()
    for key, value in context.items():
        output = output.replace(f"{{{key}}}", str(value if value is not None else ""))
    return output


def _build_diagram_navigation(bpmn_xml: str | None, current_element_id: str | None) -> dict[str, Any]:
    if not bpmn_xml:
        return {"next_candidates": []}
    try:
        root = ET.fromstring(bpmn_xml)
    except ET.ParseError:
        return {"next_candidates": []}

    elements_by_id: dict[str, dict[str, str | None]] = {}
    sequence_targets: dict[str, list[str]] = {}

    for element in root.iter():
        tag_name = _strip_namespace(element.tag)
        element_id = element.attrib.get("id")
        if not element_id:
            continue
        if tag_name == "sequenceFlow":
            source_ref = element.attrib.get("sourceRef")
            target_ref = element.attrib.get("targetRef")
            if source_ref and target_ref:
                sequence_targets.setdefault(source_ref, []).append(target_ref)
            continue
        if tag_name.endswith("Process") or tag_name in {"definitions", "lane", "laneSet"}:
            continue
        elements_by_id[element_id] = {
            "element_id": element_id,
            "element_name": element.attrib.get("name"),
            "element_type": tag_name,
        }

    candidates = []
    for target_id in sequence_targets.get(current_element_id or "", []):
        candidate = dict(elements_by_id.get(target_id) or {"element_id": target_id})
        if not candidate.get("element_name"):
            candidate["element_name"] = target_id
        candidates.append(candidate)

    return {"next_candidates": candidates}


def _strip_namespace(tag_name: str) -> str:
    if "}" in tag_name:
        return tag_name.split("}", 1)[1]
    return tag_name
