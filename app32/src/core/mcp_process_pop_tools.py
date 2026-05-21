from __future__ import annotations

from typing import Any

from services.process_pop_copilot_service import (
    build_process_pop_step_media_context,
    suggest_process_pop_step_description,
)


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


__all__ = ["register_process_pop_tools"]
