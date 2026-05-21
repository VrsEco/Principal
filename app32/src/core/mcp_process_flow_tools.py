from __future__ import annotations

from typing import Any, Optional

from services.process_flow_copilot_service import (
    build_activity_automation_context,
    build_process_flow_copilot_analysis,
)


def register_process_flow_tools(mcp: Any) -> None:
    """Registra tools MCP do copiloto de Fluxo BPMN/BPMS."""

    @mcp.tool()
    def analyze_process_flow_copilot_tool(company_id: int, process_id: int, diagram_status: str = "published") -> dict[str, Any]:
        """Analisa o fluxo BPMN do processo e aponta gaps de lane, POP, gateways e oportunidades de automação/conexão."""
        return {
            "ok": True,
            "analysis": build_process_flow_copilot_analysis(
                company_id=company_id,
                process_id=process_id,
                diagram_status=diagram_status,
            ),
        }

    @mcp.tool()
    def suggest_process_flow_activity_automation_tool(
        company_id: int,
        process_id: int,
        bpmn_element_id: str,
        objective: Optional[str] = None,
        diagram_status: str = "published",
    ) -> dict[str, Any]:
        """Sugere rascunhos de automação, conexão APP32/MCP/API e intervenção humana para uma atividade BPMN específica."""
        from services.process_ai_modeler_assistant_service import ProcessAIModelerAssistantService

        activity_context = build_activity_automation_context(
            company_id=company_id,
            process_id=process_id,
            bpmn_element_id=bpmn_element_id,
            diagram_status=diagram_status,
        )
        suggestion = ProcessAIModelerAssistantService.suggest(
            {
                "company_id": company_id,
                "process_id": process_id,
                "semantic_type": "ai_task",
                "element_type": activity_context.get("element_type"),
                "element_name": activity_context.get("element_name"),
                "element_id": bpmn_element_id,
                "objective": objective or activity_context.get("element_name"),
                "current_config": (activity_context.get("current_contract") or {}),
            }
        )
        return {
            "ok": True,
            "activity": activity_context,
            "suggestion": suggestion.get("suggestion") if isinstance(suggestion, dict) else suggestion,
        }


__all__ = ["register_process_flow_tools"]
