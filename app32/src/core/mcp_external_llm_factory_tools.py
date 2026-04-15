from __future__ import annotations

from typing import Any

from services.external_llm_factory_service import ExternalLLMFactoryService
from src.intelligence.mcp_contracts import APP32_EXTERNAL_LLM_FACTORY_MANIFEST, MCPResponseMeta, MCPSuccessEnvelope


def _meta(operation: str) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="external_llm_factory",
        operation=operation,
        scope="mcp_admin",
        capability=f"external_llm_factory.{operation}",
        permissions=["factory.external.read"],
        tags=["factory", "external-llm", "integration"],
    )


def register_external_llm_factory_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_external_llm_factory_surface_tool() -> dict[str, Any]:
        """Descreve a surface externa para LLMs focada na Sapiens Factory."""
        return MCPSuccessEnvelope[Any](
            data=APP32_EXTERNAL_LLM_FACTORY_MANIFEST.model_dump(mode="json"),
            meta=_meta("describe"),
            message="Manifesto da surface externa para LLM.",
        ).model_dump(mode="json")

    @mcp.tool()
    def evaluate_app32_external_llm_factory_session_tool(
        client_name: str,
        provider: str,
        use_case: str,
        requested_surface: str = "factory",
        user_id: int | None = None,
        company_id: int | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Avalia uma sessão externa de LLM e retorna a surface recomendada."""
        return MCPSuccessEnvelope[Any](
            data=ExternalLLMFactoryService.evaluate_external_session(
                {
                    "client_name": client_name,
                    "provider": provider,
                    "use_case": use_case,
                    "requested_surface": requested_surface,
                    "user_id": user_id,
                    "company_id": company_id,
                    "role": role,
                }
            ),
            meta=_meta("evaluate_session"),
            message="Avaliação da sessão externa concluída.",
        ).model_dump(mode="json")
