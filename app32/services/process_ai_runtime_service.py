from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from models import ProcessBpmnDiagram, ProcessInstance, ProcessInstanceExecution
from services.process_ai_execution_service import (
    is_ai_execution_mode,
    normalize_ai_contract_config,
)
from src.intelligence.llm import llm_expert, llm_router
from src.intelligence.tool_catalog import catalog
from src.intelligence.tool_context import reset_sapiens_context, set_sapiens_context


def execute_ai_contract(
    *,
    instance: ProcessInstance,
    execution: ProcessInstanceExecution,
    contract: Any | None,
    user_id: int | None = None,
) -> dict[str, Any]:
    execution_mode = str(getattr(execution, "execution_mode", None) or getattr(contract, "execution_mode", None) or "").strip().lower()
    if not is_ai_execution_mode(execution_mode):
        raise ValueError("Execução solicitada não é compatível com runtime de IA.")

    ai_config = normalize_ai_contract_config(
        getattr(contract, "ai_config_json", None) or {},
        execution_mode=execution_mode,
    )
    context_payload = _build_ai_context_payload(instance=instance, execution=execution, contract=contract)
    result = _invoke_ai_runtime(
        execution_mode=execution_mode,
        ai_config=ai_config,
        context_payload=context_payload,
        company_id=instance.company_id,
        user_id=user_id,
    )

    _apply_ai_result(
        instance=instance,
        execution=execution,
        contract=contract,
        ai_config=ai_config,
        result=result,
    )
    return result


def should_auto_run_ai_execution(
    *,
    execution_mode: str | None,
    status: str | None,
    trigger_on_update: bool = False,
    run_now: bool = False,
) -> bool:
    if not is_ai_execution_mode(execution_mode):
        return False
    if run_now:
        return True
    normalized_status = str(status or "").strip().lower()
    if trigger_on_update:
        return normalized_status in {"ready", "in_progress"}
    return normalized_status in {"pending", "ready", "in_progress"}


def _apply_ai_result(
    *,
    instance: ProcessInstance,
    execution: ProcessInstanceExecution,
    contract: Any | None,
    ai_config: dict[str, Any],
    result: dict[str, Any],
) -> None:
    now = datetime.utcnow()
    if not execution.started_at:
        execution.started_at = now

    metadata = dict(getattr(execution, "metadata_json", None) or {})
    metadata["ai_runtime"] = {
        "executed_at": now.isoformat(),
        "fallback_action": ai_config.get("fallback_action"),
        "min_confidence": ai_config.get("min_confidence"),
        "model_role": ai_config.get("model_role"),
    }
    execution.metadata_json = metadata
    execution.request_payload_json = _safe_jsonable(execution.request_payload_json or {})
    execution.response_payload_json = _safe_jsonable(result)

    success = bool(result.get("success"))
    confidence = float(result.get("confidence") or 0)
    low_confidence = confidence < float(ai_config.get("min_confidence") or 0)
    fallback_action = str(ai_config.get("fallback_action") or "human_review").strip().lower()

    if success and not low_confidence:
        execution.status = "completed"
        execution.completed_at = now
        execution.waiting_since = None
        execution.error_payload_json = {}
        if execution.started_at and not execution.duration_seconds:
            execution.duration_seconds = int((execution.completed_at - execution.started_at).total_seconds())
        _advance_instance_pointer(instance=instance, execution=execution, contract=contract, ai_config=ai_config, result=result)
    else:
        if fallback_action == "human_review":
            execution.status = "waiting_external"
            execution.waiting_since = now
            instance.status = "waiting_external"
        else:
            execution.status = "failed"
            instance.status = "failed"
        execution.error_payload_json = {
            "reason": "low_confidence" if low_confidence else "ai_execution_failed",
            "fallback_action": fallback_action,
            "confidence": confidence,
            "result": _safe_jsonable(result),
        }
        return

    next_candidates = _build_next_candidates(instance=instance, source_element_id=execution.bpmn_element_id)
    if not next_candidates:
        instance.status = "completed"
        if not instance.completed_at:
            instance.completed_at = now
    elif instance.status in {"pending", "waiting_external", "failed"}:
        instance.status = "in_progress"

    runtime_context = dict(getattr(instance, "runtime_context_json", None) or {})
    runtime_context["last_ai_execution"] = {
        "execution_id": execution.id,
        "execution_mode": execution.execution_mode,
        "decision": result.get("decision"),
        "confidence": confidence,
    }
    if result.get("data") is not None:
        runtime_context["last_ai_data"] = _safe_jsonable(result.get("data"))
    instance.runtime_context_json = runtime_context


def _advance_instance_pointer(
    *,
    instance: ProcessInstance,
    execution: ProcessInstanceExecution,
    contract: Any | None,
    ai_config: dict[str, Any],
    result: dict[str, Any],
) -> None:
    current_element_id = execution.bpmn_element_id or instance.current_bpmn_element_id
    if not current_element_id:
        return

    next_candidates = _build_next_candidates(instance=instance, source_element_id=current_element_id)
    if not next_candidates:
        instance.current_bpmn_element_id = current_element_id
        return

    target_element_id = None
    if execution.execution_mode == "ai_decision":
        decision = str(result.get("decision") or "").strip()
        decision_routes = dict((ai_config.get("metadata") or {}).get("decision_routes") or {})
        target_element_id = decision_routes.get(decision)
        if not target_element_id:
            for candidate in next_candidates:
                candidate_id = str(candidate.get("element_id") or "").strip().lower()
                candidate_name = str(candidate.get("element_name") or "").strip().lower()
                if decision.lower() in {candidate_id, candidate_name}:
                    target_element_id = candidate.get("element_id")
                    break
    elif len(next_candidates) == 1 and bool((ai_config.get("metadata") or {}).get("auto_advance", True)):
        target_element_id = next_candidates[0].get("element_id")

    if target_element_id:
        instance.current_bpmn_element_id = str(target_element_id)


def _build_ai_context_payload(
    *,
    instance: ProcessInstance,
    execution: ProcessInstanceExecution,
    contract: Any | None,
) -> dict[str, Any]:
    return {
        "company_id": instance.company_id,
        "process_id": instance.process_id,
        "process_instance_id": instance.id,
        "process_bpmn_diagram_id": instance.process_bpmn_diagram_id,
        "current_bpmn_element_id": instance.current_bpmn_element_id,
        "instance_title": instance.title,
        "instance_description": instance.description,
        "instance_status": instance.status,
        "runtime_context": _safe_jsonable(getattr(instance, "runtime_context_json", None) or {}),
        "execution": {
            "execution_id": execution.id,
            "bpmn_element_id": execution.bpmn_element_id,
            "bpmn_element_name": execution.bpmn_element_name,
            "bpmn_element_type": execution.bpmn_element_type,
            "status": execution.status,
            "request_payload": _safe_jsonable(execution.request_payload_json or {}),
            "metadata": _safe_jsonable(execution.metadata_json or {}),
        },
        "contract": {
            "contract_id": getattr(contract, "id", None),
            "capability_key": getattr(contract, "capability_key", None),
            "route_name": getattr(contract, "route_name", None),
            "requires_human_gate": bool(getattr(contract, "requires_human_gate", False)),
        },
        "next_candidates": _build_next_candidates(instance=instance, source_element_id=execution.bpmn_element_id or instance.current_bpmn_element_id),
    }


def _invoke_ai_runtime(
    *,
    execution_mode: str,
    ai_config: dict[str, Any],
    context_payload: dict[str, Any],
    company_id: int,
    user_id: int | None,
) -> dict[str, Any]:
    llm = llm_expert if ai_config.get("model_role") == "expert" else llm_router
    allowed_tools = _resolve_allowed_tools(ai_config)
    use_tools = bool(allowed_tools) and ai_config.get("tool_source") == "mcp"
    model = llm.bind_tools(allowed_tools) if use_tools else llm

    messages: list[Any] = [
        SystemMessage(content=_build_system_prompt(execution_mode=execution_mode, ai_config=ai_config)),
        HumanMessage(content=_build_user_prompt(ai_config=ai_config, context_payload=context_payload)),
    ]

    token = set_sapiens_context(user_id=user_id, company_id=company_id, channel="web", metadata={"source": "process_ai_runtime"})
    try:
        for _ in range(4):
            response = model.invoke(messages)
            if use_tools and getattr(response, "tool_calls", None):
                messages.append(response)
                for tool_call in response.tool_calls:
                    tool_message = _execute_bound_tool(tool_call, allowed_tools, company_id=company_id, user_id=user_id)
                    messages.append(tool_message)
                continue
            content = getattr(response, "content", "") or ""
            parsed = _parse_ai_json_response(content)
            if parsed is None:
                return {
                    "success": False,
                    "confidence": 0,
                    "decision": None,
                    "data": {},
                    "warnings": ["invalid_json_response"],
                    "raw_content": str(content),
                }
            return _normalize_llm_result(parsed, execution_mode=execution_mode, ai_config=ai_config)
    finally:
        reset_sapiens_context(token)

    return {
        "success": False,
        "confidence": 0,
        "decision": None,
        "data": {},
        "warnings": ["max_tool_iterations_reached"],
    }


def _resolve_allowed_tools(ai_config: dict[str, Any]) -> list[Any]:
    allowed_names = set(ai_config.get("allowed_tools") or [])
    if not allowed_names:
        return []
    return [tool for tool in catalog.get_langchain_tools() if getattr(tool, "name", None) in allowed_names]


def _execute_bound_tool(tool_call: dict[str, Any], tools: list[Any], *, company_id: int, user_id: int | None) -> ToolMessage:
    tool_name = str(tool_call.get("name") or "").strip()
    tool = next((item for item in tools if getattr(item, "name", None) == tool_name), None)
    if tool is None:
        payload = {"success": False, "error": f"Tool não permitida: {tool_name}"}
    else:
        args = tool_call.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        args.setdefault("company_id", company_id)
        if user_id is not None:
            args.setdefault("user_id", user_id)
        payload = _safe_jsonable(tool.invoke(args))
    return ToolMessage(
        content=json.dumps(payload, ensure_ascii=False, default=str),
        tool_call_id=str(tool_call.get("id") or tool_name or "tool_call"),
    )


def _build_system_prompt(*, execution_mode: str, ai_config: dict[str, Any]) -> str:
    base = [
        "Você é o executor BPMS do APP32.",
        "Retorne exclusivamente JSON válido.",
        "Não invente dados. Se faltar informação, use null.",
        "confidence deve ficar entre 0 e 1.",
    ]
    if execution_mode == "ai_decision":
        base.append(f"As decisões permitidas são: {', '.join(ai_config.get('allowed_decisions') or [])}.")
        base.append("Escolha somente uma decisão dentre as permitidas.")
    if ai_config.get("output_schema"):
        base.append(f"Respeite este output_schema: {json.dumps(ai_config.get('output_schema'), ensure_ascii=False)}")
    return "\n".join(base)


def _build_user_prompt(*, ai_config: dict[str, Any], context_payload: dict[str, Any]) -> str:
    return (
        f"INSTRUCTION:\n{ai_config.get('instruction')}\n\n"
        f"CONTEXTO:\n{json.dumps(_safe_jsonable(context_payload), ensure_ascii=False, default=str)}\n\n"
        "FORMATO OBRIGATÓRIO PARA ai_task:\n"
        '{"success": true, "confidence": 0.0, "decision": null, "reasoning_summary": "", "data": {}, "warnings": []}\n'
        "FORMATO OBRIGATÓRIO PARA ai_decision:\n"
        '{"success": true, "confidence": 0.0, "decision": "opcao", "reasoning_summary": "", "data": {}, "warnings": []}'
    )


def _parse_ai_json_response(content: Any) -> dict[str, Any] | None:
    text = str(content or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            return None

    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except json.JSONDecodeError:
            return None
    return None


def _normalize_llm_result(raw: dict[str, Any], *, execution_mode: str, ai_config: dict[str, Any]) -> dict[str, Any]:
    decision = raw.get("decision")
    if execution_mode == "ai_decision":
        allowed = set(ai_config.get("allowed_decisions") or [])
        if str(decision or "").strip() not in allowed:
            return {
                "success": False,
                "confidence": 0,
                "decision": decision,
                "data": _safe_jsonable(raw.get("data") or {}),
                "warnings": ["decision_outside_allowlist"],
                "reasoning_summary": raw.get("reasoning_summary") or "",
            }

    return {
        "success": bool(raw.get("success", True)),
        "confidence": _coerce_confidence(raw.get("confidence")),
        "decision": decision,
        "reasoning_summary": str(raw.get("reasoning_summary") or "").strip(),
        "data": _safe_jsonable(raw.get("data") or {}),
        "warnings": list(raw.get("warnings") or []),
    }


def _coerce_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _build_next_candidates(*, instance: ProcessInstance, source_element_id: str | None) -> list[dict[str, Any]]:
    if not source_element_id:
        return []
    diagram = _resolve_diagram(instance)
    if not diagram or not diagram.bpmn_xml:
        return []
    try:
        root = ET.fromstring(diagram.bpmn_xml)
    except ET.ParseError:
        return []

    sequence_targets: dict[str, list[str]] = {}
    elements_by_id: dict[str, dict[str, Any]] = {}
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
        elements_by_id[element_id] = {
            "element_id": element_id,
            "element_name": element.attrib.get("name"),
            "element_type": tag_name,
        }

    return [
        elements_by_id[target_id]
        for target_id in sequence_targets.get(source_element_id, [])
        if target_id in elements_by_id
    ]


def _resolve_diagram(instance: ProcessInstance) -> ProcessBpmnDiagram | None:
    if getattr(instance, "process_bpmn_diagram_id", None):
        diagram = ProcessBpmnDiagram.query.filter_by(
            id=instance.process_bpmn_diagram_id,
            company_id=instance.company_id,
        ).first()
        if diagram:
            return diagram
    return (
        ProcessBpmnDiagram.query
        .filter_by(process_id=instance.process_id, company_id=instance.company_id, status="published")
        .order_by(ProcessBpmnDiagram.version.desc(), ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    if ":" in tag:
        return tag.split(":", 1)[1]
    return tag


def _safe_jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False, default=str)
        return value
    except TypeError:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
