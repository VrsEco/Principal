from __future__ import annotations

from typing import Any, Dict, List


def _items(*entries: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(entry) for entry in entries]


EXACT_WORKFLOW_CONTRACTS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "project_task.create": {
        "channels": _items(
            {"name": "web", "status": "ready", "note": "Uso operacional no portal."},
            {"name": "whatsapp", "status": "ready", "note": "Fluxo conversacional já suportado."},
        ),
        "api_mcp_contracts": _items(
            {"name": "POST /api/project-tasks", "kind": "REST", "status": "planned", "note": "Contrato REST ainda precisa ser explicitamente catalogado."},
            {"name": "project_task.create", "kind": "MCP", "status": "ready", "note": "Ação canônica do workflow."},
        ),
        "tools": _items(
            {"name": "create_project_task", "status": "planned", "note": "Tool dedicada ainda será consolidada no catálogo de Tools."},
        ),
    },
    "project_task.complete": {
        "channels": _items(
            {"name": "web", "status": "ready", "note": "Operação disponível no portal."},
            {"name": "whatsapp", "status": "ready", "note": "Exige confirmação e contexto correto."},
        ),
        "api_mcp_contracts": _items(
            {"name": "project_task.complete", "kind": "MCP", "status": "ready", "note": "Ação canônica para conclusão."},
        ),
        "tools": _items(
            {"name": "complete_project_task", "status": "planned", "note": "Tool específica ainda será materializada no catálogo."},
        ),
    },
    "meeting.start": {
        "channels": _items(
            {"name": "web", "status": "ready", "note": "Suporte via portal."},
            {"name": "whatsapp", "status": "ready", "note": "Canal sujeito a human gate."},
            {"name": "telegram", "status": "ready", "note": "Canal sujeito a human gate."},
        ),
        "api_mcp_contracts": _items(
            {"name": "meeting.start", "kind": "MCP", "status": "ready", "note": "Ação operacional de início de reunião."},
        ),
        "tools": _items(
            {"name": "start_meeting", "status": "planned", "note": "Tool dedicada será consolidada em Tools."},
        ),
    },
}


PREFIX_WORKFLOW_CONTRACTS: list[tuple[str, dict[str, list[dict[str, Any]]]]] = [
    (
        "summary.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Consultas disponíveis no portal."},
                {"name": "whatsapp", "status": "ready", "note": "Resumo conversacional já observado."},
                {"name": "telegram", "status": "ready", "note": "Resumo conversacional já observado."},
            ),
            "api_mcp_contracts": _items(
                {"name": "summary.read", "kind": "MCP", "status": "ready", "note": "Família canônica de resumos."},
            ),
            "tools": _items(
                {"name": "get_plan_diagnostics", "status": "planned", "note": "Mapeamento com tools analíticas ainda será consolidado."},
            ),
        },
    ),
    (
        "my_work.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Consulta operacional disponível."},
                {"name": "whatsapp", "status": "ready", "note": "Fluxo conversacional já suportado."},
            ),
            "api_mcp_contracts": _items(
                {"name": "my_work.read", "kind": "MCP", "status": "ready", "note": "Família canônica de consulta de trabalho."},
            ),
            "tools": _items(
                {"name": "get_my_work", "status": "ready", "note": "Tool publicada no catálogo de Tools."},
            ),
        },
    ),
    (
        "project_task.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Gestão operacional no portal."},
                {"name": "whatsapp", "status": "ready", "note": "Interação conversacional disponível."},
            ),
            "api_mcp_contracts": _items(
                {"name": "project_task.runtime", "kind": "MCP", "status": "ready", "note": "Família canônica de workflows de atividade."},
            ),
            "tools": _items(
                {"name": "project_task_toolkit", "status": "planned", "note": "Conjunto tool-first ainda em consolidação."},
            ),
        },
    ),
    (
        "process_instance.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Execução via portal."},
            ),
            "api_mcp_contracts": _items(
                {"name": "process_instance.runtime", "kind": "MCP", "status": "ready", "note": "Família canônica de instâncias de processo."},
            ),
            "tools": _items(
                {"name": "process_instance_toolkit", "status": "planned", "note": "Toolset ainda será explicitado."},
            ),
        },
    ),
    (
        "meeting.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Suporte via portal."},
                {"name": "whatsapp", "status": "ready", "note": "Uso conversacional suportado."},
                {"name": "telegram", "status": "ready", "note": "Uso conversacional suportado."},
            ),
            "api_mcp_contracts": _items(
                {"name": "meeting.runtime", "kind": "MCP", "status": "ready", "note": "Família canônica de reuniões."},
            ),
            "tools": _items(
                {"name": "meeting_toolkit", "status": "planned", "note": "Toolset de reuniões será detalhado."},
            ),
        },
    ),
    (
        "collaborator.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Consulta operacional disponível."},
                {"name": "whatsapp", "status": "ready", "note": "Consulta conversacional disponível."},
            ),
            "api_mcp_contracts": _items(
                {"name": "collaborator.read", "kind": "MCP", "status": "ready", "note": "Família de consulta de colaboradores."},
            ),
            "tools": _items(
                {"name": "consult_collaborator_capacity", "status": "planned", "note": "Tool dedicada ainda será consolidada."},
            ),
        },
    ),
    (
        "onboarding.",
        {
            "channels": _items(
                {"name": "web", "status": "ready", "note": "Fluxo suportado no portal."},
                {"name": "telegram", "status": "ready", "note": "Interações remotas já previstas."},
            ),
            "api_mcp_contracts": _items(
                {"name": "onboarding.runtime", "kind": "MCP", "status": "ready", "note": "Família de onboarding."},
            ),
            "tools": _items(
                {"name": "onboarding_toolkit", "status": "planned", "note": "Toolset ainda será explicitado."},
            ),
        },
    ),
]


def resolve_workflow_contracts(action_key: str) -> dict[str, list[dict[str, Any]]]:
    normalized = str(action_key or "").strip().lower()
    resolved: dict[str, list[dict[str, Any]]] = {}

    exact = EXACT_WORKFLOW_CONTRACTS.get(normalized) or {}
    for key, items in exact.items():
        resolved[key] = [dict(item) for item in items]

    for prefix, items_by_group in PREFIX_WORKFLOW_CONTRACTS:
        if not normalized.startswith(prefix):
            continue
        for group, items in items_by_group.items():
            current = resolved.setdefault(group, [])
            for item in items:
                candidate = dict(item)
                if candidate not in current:
                    current.append(candidate)

    return resolved
