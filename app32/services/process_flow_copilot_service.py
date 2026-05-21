from __future__ import annotations

from typing import Any

from models import Process, ProcessActivityExecutionContract, ProcessRoutine
from services.ai_automation_registry_service import AIAutomationRegistryService
from services.integration_catalog_service import IntegrationCatalogService
from services.process_bpmn_graph_service import parse_bpmn_graph
from services.process_bpmn_service import get_latest_diagram
from services.process_execution_mode_service import get_execution_templates


_KEYWORD_RULES: tuple[dict[str, Any], ...] = (
    {
        "name": "document_ai_extract",
        "keywords": ("documento", "nf", "nota fiscal", "boleto", "anexo", "arquivo", "pdf", "xml"),
        "templates": ("ai_extract_document", "finance_page_editor", "mcp_register_document"),
        "integrations": ("erp_accounting_bridge", "open_finance"),
        "automation_score": 90,
        "rationale": "A atividade parece lidar com documentos estruturados e favorece extração assistida, registro no APP32 e integração financeira.",
    },
    {
        "name": "approval_human_gate",
        "keywords": ("aprovar", "aprovação", "validar", "conferir", "revisar", "autorizar"),
        "templates": ("approval_form_drawer",),
        "integrations": ("erp_accounting_bridge",),
        "automation_score": 68,
        "rationale": "A atividade exige decisão humana estruturada; o melhor ganho é abrir tarefa/formulário com dados já contextualizados.",
    },
    {
        "name": "notification_outbound",
        "keywords": ("enviar", "notificar", "avisar", "comunicar", "cobrar", "lembrar"),
        "templates": ("email_notification_api", "whatsapp_notification_api", "generic_webhook_outbound"),
        "integrations": ("service_email", "service_whatsapp", "service_telegram", "service_instagram"),
        "automation_score": 82,
        "rationale": "A atividade tem perfil de comunicação outbound e pode ser automatizada via canais externos ou webhook.",
    },
    {
        "name": "system_entry_or_update",
        "keywords": ("cadastrar", "registrar", "lançar", "atualizar", "preencher", "protocolar"),
        "templates": ("finance_page_editor", "mcp_register_document"),
        "integrations": ("erp_accounting_bridge", "financial_data_api"),
        "automation_score": 74,
        "rationale": "A atividade parece um lançamento operacional; o copiloto pode sugerir APP32 page, MCP task ou ponte sistêmica.",
    },
    {
        "name": "system_integration",
        "keywords": ("integrar", "sincronizar", "importar", "exportar", "webhook", "api", "erp"),
        "templates": ("erp_api_post", "generic_webhook_outbound"),
        "integrations": ("erp_accounting_bridge", "financial_data_api", "open_finance"),
        "automation_score": 88,
        "rationale": "A atividade já explicita integração entre sistemas e costuma caber melhor em api_task ou webhook governado.",
    },
    {
        "name": "classification_or_triage",
        "keywords": ("classificar", "triagem", "rotear", "distribuir", "conciliar"),
        "templates": ("ai_extract_document", "ai_route_gateway"),
        "integrations": ("open_finance",),
        "automation_score": 84,
        "rationale": "A atividade tem perfil de decisão/classificação assistida, com potencial de IA governada e rotas fechadas.",
    },
)


def build_process_flow_copilot_analysis(
    *,
    company_id: int,
    process_id: int,
    diagram_status: str = "published",
) -> dict[str, Any]:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if not process:
        raise ValueError("Processo não encontrado para a empresa ativa.")

    diagram = get_latest_diagram(process_id=process.id, company_id=company_id, status=diagram_status)
    if diagram is None and diagram_status != "draft":
        diagram = get_latest_diagram(process_id=process.id, company_id=company_id)

    graph = parse_bpmn_graph(getattr(diagram, "bpmn_xml", None))
    contracts = _load_contracts_map(company_id=company_id, process_id=process.id)
    pop_map = _load_pop_map(company_id=company_id, process_id=process.id)
    templates = _templates_by_key()
    integrations = _integrations_by_key()
    automation_registry = AIAutomationRegistryService.build_registry(None)

    activities = [
        _build_activity_analysis(
            activity=node,
            process=process,
            current_contract=contracts.get(node["id"]),
            pop_binding=pop_map.get(node["id"]),
            templates=templates,
            integrations=integrations,
            automation_registry=automation_registry,
        )
        for node in graph.get("activities", [])
    ]
    gateways = [_build_gateway_analysis(node=node) for node in graph.get("gateways", [])]
    warnings = _build_flow_warnings(activities=activities, gateways=gateways, graph=graph)

    return {
        "process": {
            "id": process.id,
            "company_id": process.company_id,
            "code": process.code,
            "name": process.name,
        },
        "diagram": {
            "id": getattr(diagram, "id", None),
            "status": getattr(diagram, "status", None),
            "version": getattr(diagram, "version", None),
            "updated_at": getattr(getattr(diagram, "updated_at", None), "isoformat", lambda: getattr(diagram, "updated_at", None))(),
        },
        "summary": {
            **(graph.get("metrics") or {}),
            "activities_with_lane": sum(1 for item in activities if item.get("lane_name")),
            "activities_without_lane": sum(1 for item in activities if not item.get("lane_name")),
            "activities_with_pop": sum(1 for item in activities if item.get("has_pop")),
            "activities_without_pop": sum(1 for item in activities if not item.get("has_pop")),
            "activities_with_contract": sum(1 for item in activities if item.get("current_contract")),
            "high_automation_opportunities": sum(1 for item in activities if int(item.get("automation_score") or 0) >= 80),
            "warnings": len(warnings),
        },
        "lanes": graph.get("lanes", []),
        "activities": activities,
        "gateways": gateways,
        "warnings": warnings,
    }


def build_activity_automation_context(
    *,
    company_id: int,
    process_id: int,
    bpmn_element_id: str,
    diagram_status: str = "published",
) -> dict[str, Any]:
    analysis = build_process_flow_copilot_analysis(
        company_id=company_id,
        process_id=process_id,
        diagram_status=diagram_status,
    )
    activity = next(
        (item for item in analysis.get("activities", []) if item.get("element_id") == bpmn_element_id),
        None,
    )
    if activity is None:
        raise ValueError("Atividade BPMN não encontrada no diagrama selecionado.")
    return activity


def _build_activity_analysis(
    *,
    activity: dict[str, Any],
    process: Process,
    current_contract: ProcessActivityExecutionContract | None,
    pop_binding: ProcessRoutine | None,
    templates: dict[str, dict[str, Any]],
    integrations: dict[str, dict[str, Any]],
    automation_registry: dict[str, Any],
) -> dict[str, Any]:
    text = _activity_search_text(activity)
    rule_matches = [rule for rule in _KEYWORD_RULES if any(keyword in text for keyword in rule["keywords"])]
    template_candidates = _collect_template_candidates(
        activity=activity,
        rule_matches=rule_matches,
        templates=templates,
    )
    integration_candidates = _collect_integration_candidates(
        rule_matches=rule_matches,
        integrations=integrations,
    )
    automation_candidates = _collect_internal_automation_candidates(
        rule_matches=rule_matches,
        automation_registry=automation_registry,
    )
    warnings = _activity_warnings(activity=activity, current_contract=current_contract, pop_binding=pop_binding)
    automation_score = max((int(rule["automation_score"]) for rule in rule_matches), default=35)
    if current_contract is not None:
        automation_score = max(automation_score, 55)
    if not activity.get("lane_name"):
        automation_score = max(automation_score - 10, 10)

    return {
        "element_id": activity["id"],
        "element_name": activity.get("name") or activity["id"],
        "element_type": activity.get("type"),
        "lane_id": activity.get("lane_id"),
        "lane_name": activity.get("lane_name"),
        "incoming_count": activity.get("incoming_count", 0),
        "outgoing_count": activity.get("outgoing_count", 0),
        "outgoing_edges": activity.get("outgoing_edges", []),
        "has_pop": pop_binding is not None,
        "pop_binding": _serialize_pop_binding(pop_binding),
        "current_contract": _serialize_contract(current_contract),
        "current_execution_mode": getattr(current_contract, "execution_mode", None),
        "automation_score": automation_score,
        "automation_candidates": template_candidates,
        "integration_candidates": integration_candidates,
        "internal_automation_candidates": automation_candidates,
        "recommended_next_step": _recommended_next_step(current_contract, template_candidates, warnings),
        "human_review_required": True,
        "warnings": warnings,
        "rationales": [rule["rationale"] for rule in rule_matches],
    }


def _build_gateway_analysis(*, node: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    outgoing_edges = list(node.get("outgoing_edges", []))
    if int(node.get("outgoing_count", 0) or 0) > 1 and not any(
        edge.get("condition") or edge.get("name") or edge.get("is_default_flow")
        for edge in outgoing_edges
    ):
        warnings.append("Gateway com múltiplas saídas sem condição explícita ou fluxo default identificado.")
    if int(node.get("incoming_count", 0) or 0) > 1 and int(node.get("outgoing_count", 0) or 0) > 1:
        warnings.append("Gateway mistura fan-in e fan-out; revisar semântica de split/join com intervenção humana.")
    return {
        "element_id": node["id"],
        "element_name": node.get("name") or node["id"],
        "element_type": node.get("type"),
        "incoming_count": node.get("incoming_count", 0),
        "outgoing_count": node.get("outgoing_count", 0),
        "outgoing_edges": outgoing_edges,
        "human_review_required": True,
        "warnings": warnings,
    }


def _build_flow_warnings(
    *,
    activities: list[dict[str, Any]],
    gateways: list[dict[str, Any]],
    graph: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if (graph.get("metrics") or {}).get("lanes", 0) == 0:
        warnings.append("O fluxo não possui lanes mapeadas; o copiloto não consegue inferir executor visual por swimlane.")
    if any(not activity.get("lane_name") for activity in activities):
        warnings.append("Há atividades executáveis sem lane explícita; revisar executor visual antes de automatizar.")
    if any(gateway.get("warnings") for gateway in gateways):
        warnings.append("Há gateways que exigem revisão humana para garantir semântica correta de split/join.")
    if any(not activity.get("has_pop") for activity in activities):
        warnings.append("Existem atividades sem POP vinculado; automatizar antes de fechar a operação pode gerar drift.")
    return warnings


def _collect_template_candidates(
    *,
    activity: dict[str, Any],
    rule_matches: list[dict[str, Any]],
    templates: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in rule_matches:
        for template_key in rule["templates"]:
            template = templates.get(template_key)
            if not template or template_key in seen:
                continue
            seen.add(template_key)
            candidates.append(
                {
                    "candidate_key": f"template:{template_key}",
                    "kind": "app32_template",
                    "title": template.get("label"),
                    "summary": template.get("summary"),
                    "execution_mode": template.get("execution_mode"),
                    "template_key": template_key,
                    "fit_score": int(rule["automation_score"]),
                    "rationale": rule["rationale"],
                    "human_review_required": True,
                    "draft_contract": _draft_contract_from_template(template, activity=activity),
                }
            )
    if not candidates:
        candidates.append(
            {
                "candidate_key": "template:manual_review",
                "kind": "human_review",
                "title": "Manter revisão humana",
                "summary": "A atividade ainda depende de desenho semântico/visual humano antes de virar contrato automático.",
                "execution_mode": "human_task",
                "template_key": None,
                "fit_score": 40,
                "rationale": "Sem heurística forte de automação; melhor abrir tarefa humana no APP32 e amadurecer o binding depois.",
                "human_review_required": True,
                "draft_contract": {
                    "execution_mode": "human_task",
                    "interaction_mode": "drawer",
                    "capability_key": "process.flow_copilot.human_review",
                    "route_name": None,
                },
            }
        )
    return candidates


def _collect_integration_candidates(
    *,
    rule_matches: list[dict[str, Any]],
    integrations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in rule_matches:
        for integration_key in rule["integrations"]:
            integration = integrations.get(integration_key)
            if not integration or integration_key in seen:
                continue
            seen.add(integration_key)
            technical_channel = str(integration.get("technical_channel") or "api").strip().lower()
            execution_mode = "mcp_task" if technical_channel == "mcp" else "api_task"
            if technical_channel == "api_mcp":
                execution_mode = "api_task"
            candidates.append(
                {
                    "candidate_key": f"integration:{integration_key}",
                    "kind": "external_integration",
                    "title": integration.get("title"),
                    "summary": integration.get("summary"),
                    "execution_mode": execution_mode,
                    "technical_channel": technical_channel,
                    "status": integration.get("status"),
                    "fit_score": int(rule["automation_score"]) - 2,
                    "rationale": rule["rationale"],
                    "human_review_required": True,
                }
            )
    return candidates


def _collect_internal_automation_candidates(
    *,
    rule_matches: list[dict[str, Any]],
    automation_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    items = list((automation_registry or {}).get("automations") or [])
    if not items:
        return candidates
    text = " ".join(rule["name"] for rule in rule_matches)
    for item in items:
        key = str(item.get("key") or "")
        if "routine" in text and "routine" in key:
            candidates.append(
                {
                    "candidate_key": f"automation:{key}",
                    "kind": "internal_automation",
                    "title": item.get("title"),
                    "summary": item.get("description"),
                    "execution_mode": item.get("execution_mode"),
                    "status": item.get("status"),
                    "human_review_required": True,
                }
            )
        if any(token in text for token in ("document", "classification")) and "financial_automation" in key:
            candidates.append(
                {
                    "candidate_key": f"automation:{key}",
                    "kind": "internal_automation",
                    "title": item.get("title"),
                    "summary": item.get("description"),
                    "execution_mode": item.get("execution_mode"),
                    "status": item.get("status"),
                    "human_review_required": True,
                }
            )
    return candidates


def _activity_search_text(activity: dict[str, Any]) -> str:
    return " ".join(
        filter(
            None,
            [
                str(activity.get("name") or "").strip().lower(),
                str(activity.get("type") or "").strip().lower(),
                str(activity.get("lane_name") or "").strip().lower(),
            ],
        )
    )


def _activity_warnings(
    *,
    activity: dict[str, Any],
    current_contract: ProcessActivityExecutionContract | None,
    pop_binding: ProcessRoutine | None,
) -> list[str]:
    warnings: list[str] = []
    if not activity.get("lane_name"):
        warnings.append("Atividade sem lane explícita; o executor visual ainda precisa ser definido por humano.")
    if pop_binding is None:
        warnings.append("Atividade sem POP vinculado.")
    if current_contract is None:
        warnings.append("Atividade ainda sem contrato de execução configurado.")
    if int(activity.get("outgoing_count", 0) or 0) > 1:
        warnings.append("Atividade possui múltiplas saídas; revisar se o split deveria estar em um gateway dedicado.")
    return warnings


def _recommended_next_step(
    current_contract: ProcessActivityExecutionContract | None,
    template_candidates: list[dict[str, Any]],
    warnings: list[str],
) -> str:
    if current_contract is not None:
        return "revisar_contrato_existente_com_intervencao_humana"
    if template_candidates and not warnings:
        return "gerar_contrato_rascunho_e_revisar"
    return "analisar_manual_e_modelar_contrato"


def _draft_contract_from_template(template: dict[str, Any], *, activity: dict[str, Any]) -> dict[str, Any]:
    execution_mode = template.get("execution_mode")
    draft = {
        "execution_mode": execution_mode,
        "interaction_mode": template.get("ui_schema_json", {}).get("open_in") or template.get("interaction_mode"),
        "capability_key": f"process.flow_copilot.{template.get('key')}",
        "route_name": activity.get("element_name") or activity.get("id"),
        "ui_schema_json": dict(template.get("ui_schema_json") or {}),
        "rest_config_json": dict(template.get("rest_config_json") or {}),
        "mcp_config_json": dict(template.get("mcp_config_json") or {}),
        "ai_config_json": dict(template.get("ai_config_json") or {}),
    }
    return {key: value for key, value in draft.items() if value not in (None, {}, [])}


def _serialize_contract(contract: ProcessActivityExecutionContract | None) -> dict[str, Any] | None:
    if contract is None:
        return None
    return {
        "id": contract.id,
        "execution_mode": contract.execution_mode,
        "interaction_mode": contract.interaction_mode,
        "capability_key": contract.capability_key,
        "route_name": contract.route_name,
        "rest_config_json": contract.rest_config_json or {},
        "mcp_config_json": contract.mcp_config_json or {},
        "ai_config_json": contract.ai_config_json or {},
    }


def _serialize_pop_binding(pop_binding: ProcessRoutine | None) -> dict[str, Any] | None:
    if pop_binding is None:
        return None
    return {
        "id": pop_binding.id,
        "code": pop_binding.code,
        "name": pop_binding.name,
        "bpmn_element_id": pop_binding.bpmn_element_id,
    }


def _load_contracts_map(*, company_id: int, process_id: int) -> dict[str, ProcessActivityExecutionContract]:
    contracts = (
        ProcessActivityExecutionContract.query
        .filter_by(company_id=company_id, process_id=process_id, is_active=True)
        .order_by(ProcessActivityExecutionContract.version.desc(), ProcessActivityExecutionContract.id.desc())
        .all()
    )
    result: dict[str, ProcessActivityExecutionContract] = {}
    for contract in contracts:
        element_id = str(contract.bpmn_element_id or "").strip()
        if element_id and element_id not in result:
            result[element_id] = contract
    return result


def _load_pop_map(*, company_id: int, process_id: int) -> dict[str, ProcessRoutine]:
    routines = (
        ProcessRoutine.query
        .filter_by(company_id=company_id, process_id=process_id)
        .filter((ProcessRoutine.is_active.is_(True)) | (ProcessRoutine.is_active.is_(None)))
        .all()
    )
    result: dict[str, ProcessRoutine] = {}
    for routine in routines:
        element_id = str(routine.bpmn_element_id or "").strip()
        if element_id and element_id not in result:
            result[element_id] = routine
    return result


def _templates_by_key() -> dict[str, dict[str, Any]]:
    return {
        str(item.get("key")): dict(item)
        for item in get_execution_templates()
        if item.get("key")
    }


def _integrations_by_key() -> dict[str, dict[str, Any]]:
    try:
        payload = IntegrationCatalogService.build_catalog()
    except Exception:
        payload = {"integrations": []}
    return {
        str(item.get("key")): dict(item)
        for item in (payload.get("integrations") or [])
        if item.get("key")
    }

