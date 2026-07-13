from __future__ import annotations

from typing import Any

from services.process_pop_copilot_service import (
    build_process_pop_step_media_context,
    suggest_process_pop_step_description,
)
from services.process_pop_mcp_service import attach_static_image_to_pop_step, create_pop_step_for_bpmn


def register_process_pop_tools(mcp: Any) -> None:
    """Registra tools MCP iniciais para o POP Copilot com vídeo curto por passo."""

    @mcp.tool()
    def get_process_pop_step_media_context_tool(company_id: int, step_id: int) -> dict[str, Any]:
        """Retorna o contexto multimídia de um passo POP, incluindo vídeo curto, print e próximos passos recomendados."""
        return {
            "ok": True,
            "context": build_process_pop_step_media_context(company_id=company_id, step_id=step_id),
        }

    @mcp.tool()
    def draft_process_pop_step_description_tool(company_id: int, step_id: int) -> dict[str, Any]:
        """Gera um rascunho inicial da descrição de um passo POP usando narração, vídeo curto, print e contexto da atividade."""
        return {
            "ok": True,
            **suggest_process_pop_step_description(company_id=company_id, step_id=step_id),
        }

    @mcp.tool()
    def create_process_pop_step_for_bpmn_tool(company_id: int, process_id: int, bpmn_element_id: str, name: str, description: str | None = None, expected_result: str | None = None, bpmn_element_name: str | None = None, bpmn_element_type: str | None = None, order_index: int | None = None) -> dict[str, Any]:
        """Cria um passo POP vinculado a uma atividade BPMN, criando o binding quando necessário."""
        return {"ok": True, **create_pop_step_for_bpmn(company_id=company_id, process_id=process_id, bpmn_element_id=bpmn_element_id, name=name, description=description, expected_result=expected_result, bpmn_element_name=bpmn_element_name, bpmn_element_type=bpmn_element_type, order_index=order_index)}

    @mcp.tool()
    def attach_process_pop_step_static_image_tool(company_id: int, step_id: int, image_base64: str, filename: str = "pop-step.png", content_type: str | None = None) -> dict[str, Any]:
        """Anexa evidência JPG/PNG; image_base64 deve conter apenas o conteúdo Base64."""
        return {"ok": True, **attach_static_image_to_pop_step(company_id=company_id, step_id=step_id, image_base64=image_base64, filename=filename, content_type=content_type)}


__all__ = ["register_process_pop_tools"]
