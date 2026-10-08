from __future__ import annotations

from typing import Any

from services.knowledge.query_service import KnowledgeQueryService
from src.core.mcp_runtime import resolve_mcp_execution_context


_MAX_LIMIT = 20
_MAX_QUESTION_CHARS = 2000

# Única exceção à regra "ferramentas de conhecimento não recebem company_id" (emenda de
# 2026-10-08 da SPEC rag_mcp_governado_squads_v1): estas duas só ACEITAM company_id como
# SELEÇÃO entre empresas que o grant do principal já autoriza; nunca como identidade confiável.
SECURE_COMPANY_SELECTION_TOOLS = (
    "search_organizational_knowledge_secure",
    "answer_organizational_question_secure",
)


def _validated_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit deve ser um inteiro.")
    if limit < 1 or limit > _MAX_LIMIT:
        raise ValueError(f"limit deve estar entre 1 e {_MAX_LIMIT}.")
    return limit


def _validated_question(question: str) -> str:
    text = str(question or "").strip()
    if not text:
        raise ValueError("question não pode ser vazia.")
    if len(text) > _MAX_QUESTION_CHARS:
        raise ValueError(f"question deve ter no máximo {_MAX_QUESTION_CHARS} caracteres.")
    return text


def _context_for_company(company_id: int):
    """Resolve o contexto pedindo a empresa EXPLICITAMENTE (valida o grant do principal)."""
    if isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0:
        raise ValueError("company_id deve ser um inteiro positivo.")
    context = resolve_mcp_execution_context({"company_id": company_id})
    if context.company_id != company_id:  # defesa em profundidade: nunca ler outra empresa
        raise PermissionError("empresa resolvida difere da solicitada.")
    return context


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

    @mcp.tool()
    def search_organizational_knowledge_secure(company_id: int, question: str, limit: int = 5) -> dict[str, Any]:
        """Busca conhecimento autorizado de UMA empresa (company_id explícito); somente leitura."""

        text = _validated_question(question)
        bounded = _validated_limit(limit)
        context = _context_for_company(company_id)
        return service.search(
            text,
            company_id=company_id,
            limit=bounded,
            require_company=True,
            user_id=context.user_id,
            employee_id=context.employee_id,
        )

    @mcp.tool()
    def answer_organizational_question_secure(company_id: int, question: str, limit: int = 5) -> dict[str, Any]:
        """Responde pergunta organizacional de UMA empresa, com claims e citações; somente leitura."""

        text = _validated_question(question)
        bounded = _validated_limit(limit)
        context = _context_for_company(company_id)
        return service.answer(
            text,
            company_id=company_id,
            limit=bounded,
            require_company=True,
            user_id=context.user_id,
            employee_id=context.employee_id,
        )


__all__ = ["register_knowledge_tools", "SECURE_COMPANY_SELECTION_TOOLS"]
