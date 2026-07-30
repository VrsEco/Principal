from __future__ import annotations

from typing import Any

from services.knowledge.query_service import KnowledgeQueryService
from src.core.mcp_runtime import resolve_mcp_execution_context


def register_knowledge_tools(mcp: Any) -> None:
    """Registra leitura de conhecimento sem aceitar tenant vindo do usuário."""

    service = KnowledgeQueryService()

    @mcp.tool()
    def answer_product_help(question: str, limit: int = 3) -> dict[str, Any]:
        """Responde como usar o APP Versus com evidências do manual oficial."""

        context = resolve_mcp_execution_context({})
        return service.answer(
            question,
            company_id=context.company_id,
            source_types=("product_help",),
            limit=limit,
            require_company=False,
            user_id=context.user_id,
            employee_id=context.employee_id,
        )

    @mcp.tool()
    def search_organizational_knowledge(
        question: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Busca conhecimento autorizado da empresa ativa e conteúdo oficial do produto."""

        context = resolve_mcp_execution_context({})
        return service.search(
            question,
            company_id=context.company_id,
            limit=limit,
            require_company=True,
            user_id=context.user_id,
            employee_id=context.employee_id,
        )

    @mcp.tool()
    def answer_organizational_question(
        question: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Responde pergunta organizacional com claims e citações autorizadas."""

        context = resolve_mcp_execution_context({})
        return service.answer(
            question,
            company_id=context.company_id,
            limit=limit,
            require_company=True,
            user_id=context.user_id,
            employee_id=context.employee_id,
        )


__all__ = ["register_knowledge_tools"]
