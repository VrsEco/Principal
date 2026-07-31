from __future__ import annotations

from typing import Any, Iterable

from services.knowledge.query_service import (
    KnowledgeQueryError,
    KnowledgeQueryService,
    KnowledgeTenantContextError,
)


class KnowledgeInteractionService:
    """Orquestra a experiência web sem confiar em tenant vindo do navegador."""

    VALID_SCOPES = {"company", "product", "all"}
    MAX_SOURCE_TYPES = 12
    PRODUCT_SOURCE_TYPES = ("product_help", "system_documentation")

    def __init__(self, query_service: KnowledgeQueryService | None = None) -> None:
        self.query_service = query_service or KnowledgeQueryService()

    def answer(
        self,
        question: str,
        *,
        scope: str,
        company_id: int | None,
        user_id: int,
        employee_id: int | None = None,
        source_types: Iterable[str] | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        normalized_scope = str(scope or "all").strip().lower()
        if normalized_scope not in self.VALID_SCOPES:
            raise KnowledgeQueryError("Escopo de conhecimento inválido.")

        normalized_types = tuple(
            dict.fromkeys(
                str(item).strip().lower()
                for item in (source_types or ())
                if str(item).strip()
            )
        )
        if len(normalized_types) > self.MAX_SOURCE_TYPES:
            raise KnowledgeQueryError("Selecione no máximo 12 tipos de fonte.")

        if normalized_scope == "product":
            query_company_id = None
            require_company = False
            include_product = True
            normalized_types = self.PRODUCT_SOURCE_TYPES
        else:
            if company_id is None:
                raise KnowledgeTenantContextError(
                    "Selecione uma empresa ativa antes de consultar o conhecimento."
                )
            query_company_id = int(company_id)
            require_company = True
            include_product = normalized_scope == "all"

        payload = self.query_service.answer(
            question,
            company_id=query_company_id,
            source_types=normalized_types,
            limit=limit,
            require_company=require_company,
            user_id=int(user_id),
            employee_id=employee_id,
            include_product=include_product,
        )
        payload["requested_scope"] = normalized_scope
        payload["presentation"] = self._presentation(payload, normalized_scope)
        return payload

    @staticmethod
    def _presentation(payload: dict[str, Any], scope: str) -> dict[str, Any]:
        citations = list(payload.get("citations") or [])
        if scope == "product":
            eyebrow = "Como usar o APP Versus"
            source_label = "Manual oficial"
        elif scope == "company":
            eyebrow = "Conhecimento da empresa"
            source_label = "Fontes autorizadas"
        else:
            eyebrow = "Resposta do Sapiens"
            source_label = "Produto e empresa"
        return {
            "eyebrow": eyebrow,
            "source_label": source_label,
            "source_count": len(citations),
            "strategy_label": (
                "Busca aprofundada"
                if len(citations) > 2
                else "Busca rápida"
            ),
        }


__all__ = ["KnowledgeInteractionService"]
