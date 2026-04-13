from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence

from models.agent_menu import AgentMenuOption
from models.workflow_gap import WorkflowGapCandidate
from models.workflow_usage import WorkflowExecutionLog
from src.intelligence.workflows.registry import WorkflowRegistry


def _normalize_text(value: Any) -> str:
    return str(value or '').strip()


def _sorted_counts(label: str, values: Dict[str, int]) -> List[Dict[str, Any]]:
    return [
        {label: key, 'count': count}
        for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]


def _option_parent_code(option: AgentMenuOption) -> Optional[str]:
    parent = getattr(option, 'parent', None)
    if parent is None:
        return None
    return _normalize_text(getattr(parent, 'code', None)) or None


def _option_parent_title(option: AgentMenuOption) -> Optional[str]:
    parent = getattr(option, 'parent', None)
    if parent is None:
        return None
    return _normalize_text(getattr(parent, 'title', None)) or None


SENSITIVE_ACTION_KEYS = {
    "project_task.complete",
    "process_instance.complete",
    "meeting.start",
}

APPROVAL_CHANNELS = {"telegram", "whatsapp", "email"}


def _collect_metadata_list(logs: Sequence[WorkflowExecutionLog], *keys: str) -> List[str]:
    values: list[str] = []
    seen: set[str] = set()
    for log in logs or []:
        metadata = getattr(log, "metadata_json", None) or {}
        if not isinstance(metadata, dict):
            continue
        for key in keys:
            raw_value = metadata.get(key)
            candidates = raw_value if isinstance(raw_value, list) else [raw_value]
            for candidate in candidates:
                normalized = _normalize_text(candidate)
                lowered = normalized.lower()
                if normalized and lowered not in seen:
                    seen.add(lowered)
                    values.append(normalized)
    return values


def _build_channel_contracts(logs: Sequence[WorkflowExecutionLog]) -> List[Dict[str, Any]]:
    channel_counts: Dict[str, int] = defaultdict(int)
    for log in logs or []:
        channel = _normalize_text(getattr(log, "channel", None)) or "web"
        channel_counts[channel] += 1

    items = [
        {
            "name": channel,
            "status": "ready",
            "note": f"{count} execução(ões) registradas neste canal.",
        }
        for channel, count in sorted(channel_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    if items:
        return items
    return [
        {
            "name": "Catálogo de canais",
            "status": "planned",
            "note": "Mapeamento por canal ainda não catalogado para este workflow.",
        }
    ]


def _build_api_mcp_contracts(logs: Sequence[WorkflowExecutionLog], action_key: str) -> List[Dict[str, Any]]:
    rest_endpoints = _collect_metadata_list(logs, "rest_endpoints", "api_endpoints")
    mcp_contracts = _collect_metadata_list(logs, "mcp_contracts", "mcp_tools")
    items: list[dict[str, Any]] = []
    items.extend(
        {
            "name": endpoint,
            "status": "ready",
            "kind": "REST",
            "note": "Observado em telemetria operacional.",
        }
        for endpoint in rest_endpoints
    )
    items.extend(
        {
            "name": contract,
            "status": "ready",
            "kind": "MCP",
            "note": "Observado em telemetria operacional.",
        }
        for contract in mcp_contracts
    )
    if items:
        return items
    return [
        {
            "name": action_key or "workflow.runtime",
            "status": "planned",
            "kind": "API/MCP",
            "note": "Contrato técnico específico ainda não foi catalogado neste workflow.",
        }
    ]


def _build_tool_contracts(logs: Sequence[WorkflowExecutionLog], action_key: str) -> List[Dict[str, Any]]:
    tools = _collect_metadata_list(logs, "tools", "tool_names", "tool_name")
    if tools:
        return [
            {
                "name": tool,
                "status": "ready",
                "note": "Tool observada em execução real.",
            }
            for tool in tools
        ]
    return [
        {
            "name": action_key or "tool-first mapping",
            "status": "planned",
            "note": "Relacionamento Tool-first ainda não modelado para este workflow.",
        }
    ]


def _build_permission_contracts(action_key: str, workflow_scope: str) -> List[Dict[str, Any]]:
    items = [
        {
            "name": "Escopo tenant",
            "status": "ready",
            "note": "Workflow respeita contexto multi-tenant por company_id.",
        },
        {
            "name": f"Escopo {workflow_scope}",
            "status": "ready",
            "note": "Definido conforme origem global/empresa do cadastro do workflow.",
        },
    ]
    if action_key in SENSITIVE_ACTION_KEYS:
        items.append(
            {
                "name": "Human gate obrigatório",
                "status": "ready",
                "note": f"Exige aprovação humana em canais: {', '.join(sorted(APPROVAL_CHANNELS))}.",
            }
        )
    else:
        items.append(
            {
                "name": "Execução automática",
                "status": "ready",
                "note": "Sem exigência de aprovação humana pela política padrão atual.",
            }
        )
    items.append(
        {
            "name": "RBAC fino",
            "status": "planned",
            "note": "Matriz detalhada de perfis/permissões ainda será catalogada.",
        }
    )
    return items


def _build_configuration_contracts(workflow: WorkflowDefinition) -> List[Dict[str, Any]]:
    items = []
    if getattr(workflow, "confirmation_template", None):
        items.append(
            {
                "name": "Template de confirmação",
                "status": "ready",
                "note": "Workflow possui etapa explícita de confirmação antes da execução.",
            }
        )
    if getattr(workflow, "execution_template", None):
        items.append(
            {
                "name": "Template de execução",
                "status": "ready",
                "note": "Workflow possui instrução de execução cadastrada.",
            }
        )
    items.append(
        {
            "name": "Parâmetros operacionais",
            "status": "planned",
            "note": "Tela de configurações específicas deste workflow ainda será construída.",
        }
    )
    return items


def build_workflow_catalog(
    *,
    options: Sequence[AgentMenuOption],
    usage_logs: Sequence[WorkflowExecutionLog],
    gap_candidates: Sequence[WorkflowGapCandidate],
    preferred_company_id: Optional[int],
) -> Dict[str, Any]:
    registry = WorkflowRegistry.from_menu_options(options, preferred_company_id=preferred_company_id)
    workflows = registry.list()

    options_by_id = {int(option.id): option for option in options if getattr(option, 'id', None) is not None}
    usage_by_code: Dict[str, List[WorkflowExecutionLog]] = defaultdict(list)
    for item in usage_logs or []:
        code = _normalize_text(getattr(item, 'workflow_code', None))
        if code:
            usage_by_code[code].append(item)

    gaps_by_code: Dict[str, List[WorkflowGapCandidate]] = defaultdict(list)
    for gap in gap_candidates or []:
        for raw_code in getattr(gap, 'matched_workflow_codes', None) or []:
            code = _normalize_text(raw_code)
            if code:
                gaps_by_code[code].append(gap)

    catalog_items: List[Dict[str, Any]] = []
    summary_channels: Dict[str, int] = defaultdict(int)
    summary_sources: Dict[str, int] = defaultdict(int)
    used_workflows = 0
    workflows_with_gaps = 0

    for workflow in workflows:
        option = options_by_id.get(int(workflow.source_option_id or 0))
        logs = usage_by_code.get(workflow.code, [])
        gaps = gaps_by_code.get(workflow.code, [])
        if logs:
            used_workflows += 1
        if gaps:
            workflows_with_gaps += 1

        channel_counts: Dict[str, int] = defaultdict(int)
        status_counts: Dict[str, int] = defaultdict(int)
        route_counts: Dict[str, int] = defaultdict(int)
        for log in logs:
            channel = _normalize_text(getattr(log, 'channel', None)) or '(sem_canal)'
            status = _normalize_text(getattr(log, 'status', None)) or '(sem_status)'
            route_source = _normalize_text(getattr(log, 'route_source', None)) or '(sem_origem)'
            channel_counts[channel] += 1
            status_counts[status] += 1
            route_counts[route_source] += 1
            summary_channels[channel] += 1
            summary_sources[route_source] += 1

        last_gap_at = None
        if gaps:
            ordered = sorted(gaps, key=lambda item: getattr(item, 'created_at', None) or 0, reverse=True)
            last_gap_at = getattr(ordered[0], 'created_at', None)

        required_fields = [field.model_dump() for field in workflow.required_fields]
        scope = 'company' if workflow.company_id is not None else 'global'
        item = {
            'code': workflow.code,
            'title': workflow.title,
            'action_key': workflow.action_key,
            'description': workflow.description,
            'sort_order': workflow.sort_order,
            'company_id': workflow.company_id,
            'scope': scope,
            'source_option_id': workflow.source_option_id,
            'parent_code': _option_parent_code(option) if option is not None else None,
            'parent_title': _option_parent_title(option) if option is not None else None,
            'required_fields': required_fields,
            'keywords': list(workflow.keywords or []),
            'intent_examples': list(workflow.intent_examples or []),
            'usage': {
                'count': int(getattr(option, 'usage_count', 0) or 0),
                'last_used_at': getattr(option, 'last_used_at', None).isoformat() if getattr(option, 'last_used_at', None) else None,
                'log_count': len(logs),
                'by_channel': _sorted_counts('channel', channel_counts),
                'by_status': _sorted_counts('status', status_counts),
                'by_route_source': _sorted_counts('route_source', route_counts),
            },
            'gaps': {
                'count': len(gaps),
                'last_gap_at': last_gap_at.isoformat() if last_gap_at else None,
            },
            'channels': _build_channel_contracts(logs),
            'api_mcp_contracts': _build_api_mcp_contracts(logs, workflow.action_key),
            'tools': _build_tool_contracts(logs, workflow.action_key),
            'permissions': _build_permission_contracts(workflow.action_key, scope),
            'configurations': _build_configuration_contracts(workflow),
            'is_active': bool(getattr(option, 'is_active', True)) if option is not None else True,
        }
        catalog_items.append(item)

    catalog_items.sort(key=lambda entry: (entry['sort_order'], entry['code']))

    return {
        'summary': {
            'workflow_count': len(catalog_items),
            'used_workflow_count': used_workflows,
            'unused_workflow_count': max(len(catalog_items) - used_workflows, 0),
            'workflow_with_gap_count': workflows_with_gaps,
            'global_workflow_count': sum(1 for item in catalog_items if item['scope'] == 'global'),
            'company_workflow_count': sum(1 for item in catalog_items if item['scope'] == 'company'),
            'channels': _sorted_counts('channel', summary_channels),
            'route_sources': _sorted_counts('route_source', summary_sources),
        },
        'workflows': catalog_items,
    }
