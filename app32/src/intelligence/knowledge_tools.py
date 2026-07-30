from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from services.knowledge.query_service import KnowledgeQueryService
from src.intelligence.tool_context import get_sapiens_context


@tool
def answer_product_help(question: str, limit: int = 3) -> dict[str, Any]:
    """Responde como usar o APP Versus com evidências do manual oficial."""

    context = get_sapiens_context()
    return KnowledgeQueryService().answer(
        question,
        company_id=context.company_id,
        source_types=("product_help",),
        limit=limit,
        require_company=False,
        user_id=context.user_id,
        employee_id=context.employee_id,
    )


@tool
def search_organizational_knowledge(
    question: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Busca conhecimento autorizado da empresa ativa e conteúdo oficial do produto."""

    context = get_sapiens_context()
    return KnowledgeQueryService().search(
        question,
        company_id=context.company_id,
        limit=limit,
        require_company=True,
        user_id=context.user_id,
        employee_id=context.employee_id,
    )


@tool
def answer_organizational_question(
    question: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Responde pergunta organizacional com claims e citações autorizadas."""

    context = get_sapiens_context()
    return KnowledgeQueryService().answer(
        question,
        company_id=context.company_id,
        limit=limit,
        require_company=True,
        user_id=context.user_id,
        employee_id=context.employee_id,
    )


knowledge_langchain_tools = (
    answer_product_help,
    search_organizational_knowledge,
    answer_organizational_question,
)


__all__ = [
    "answer_organizational_question",
    "answer_product_help",
    "knowledge_langchain_tools",
    "search_organizational_knowledge",
]
