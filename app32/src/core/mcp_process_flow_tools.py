from __future__ import annotations

from typing import Any, Optional

from services.process_flow_copilot_service import (
    build_activity_automation_context,
    build_process_flow_copilot_analysis,
)
from services.process_bpmn_activity_mcp_service import create_bpmn_activity
from services.process_modeling_publication_service import publish_approved_process_modeling_package


def register_process_flow_tools(mcp: Any) -> None:
    """Registra tools MCP do copiloto de Fluxo BPMN/BPMS."""

    @mcp.tool()
    def create_process_bpmn_activity_tool(company_id: int, process_id: int, name: str, lane_id: str | None = None, lane_name: str | None = None, source_element_id: str | None = None, target_element_id: str | None = None, order_index: int | None = None, data_object_name: str | None = None, data_object_direction: str = "input_output", data_object_id: str | None = None) -> dict[str, Any]:
        """Cria task BPMN, conexões e Data Object Reference reutilizável no diagrama draft do processo."""
        return {"ok": True, **create_bpmn_activity(company_id=company_id, process_id=process_id, name=name, lane_id=lane_id, lane_name=lane_name, source_element_id=source_element_id, target_element_id=target_element_id, order_index=order_index, data_object_name=data_object_name, data_object_direction=data_object_direction, data_object_id=data_object_id)}

    @mcp.tool()
    def publish_approved_process_modeling_package_tool(
        company_id: int,
        process_id: int,
        package: dict[str, Any],
        human_gate_confirmed: bool = False,
    ) -> dict[str, Any]:
        """Publica perfil, BPMN, POP e artefatos de uma modelagem já aprovada pelo usuário."""
        return {
            "ok": True,
            **publish_approved_process_modeling_package(
                company_id=company_id,
                process_id=process_id,
                package=package,
                human_gate_confirmed=human_gate_confirmed,
            ),
        }

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
