from __future__ import annotations

import re
import uuid
from types import SimpleNamespace
from typing import Any, Iterable

from flask import has_app_context

from models import db
from models.knowledge import KnowledgeInteraction

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
    ENGINE_VERSION = "knowledge-understanding-v1"
    PRODUCT_HELP_PATTERNS = ("como", "onde", "cadastro", "cadastrar", "publico", "publicar", "gero", "gerar", "filtro", "filtrar", "vejo", "ver")
    ROUTINE_ACTIVITY_TERMS = ("atividade", "atividades", "tarefa", "tarefas", "pendencia", "pendências", "pendencias", "meu", "minhas", "tenho")

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

        understanding = self.understand_question(
            question,
            requested_scope=normalized_scope,
            source_types=normalized_types,
        )
        direct_payload = self._direct_product_help(question, understanding)
        if direct_payload is not None:
            payload = direct_payload
            payload["requested_scope"] = normalized_scope
            payload["understanding"] = understanding
            payload["presentation"] = self._presentation(payload, normalized_scope)
            interaction = self._record_interaction(
                question=question,
                payload=payload,
                requested_scope=normalized_scope,
                company_id=query_company_id,
                user_id=int(user_id),
                employee_id=employee_id,
                understanding=understanding,
            )
            payload["interaction_id"] = interaction.interaction_uuid
            return payload

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
        payload["understanding"] = understanding
        payload["presentation"] = self._presentation(payload, normalized_scope)
        interaction = self._record_interaction(
            question=question,
            payload=payload,
            requested_scope=normalized_scope,
            company_id=query_company_id,
            user_id=int(user_id),
            employee_id=employee_id,
            understanding=understanding,
        )
        payload["interaction_id"] = interaction.interaction_uuid
        return payload


    def understand_question(
        self,
        question: str,
        *,
        requested_scope: str,
        source_types: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_question(question)
        tokens = set(normalized.split())
        source_types_set = set(source_types or ())
        signals: list[str] = []
        intent = "corporate_knowledge"
        domain = "general"
        confidence = 0.55

        if requested_scope == "product" or source_types_set.intersection(self.PRODUCT_SOURCE_TYPES):
            intent = "product_help"
            domain = "app_versus_usage"
            confidence = 0.8
            signals.append("product_scope")
        if tokens.intersection(self.PRODUCT_HELP_PATTERNS):
            intent = "product_help"
            domain = "app_versus_usage"
            confidence = max(confidence, 0.78)
            signals.append("how_to_question")
        if tokens.intersection({"api", "endpoint", "mcp", "spec", "paper", "arquitetura", "tecnico", "técnico"}):
            intent = "technical"
            domain = "architecture"
            confidence = 0.82
            signals.append("technical_terms")
        if tokens.intersection({"crie", "criar", "execute", "executar", "registre", "registrar", "lançar", "lancar"}) and "how_to_question" not in signals:
            intent = "operational_action"
            confidence = 0.72
            signals.append("action_verbs")
        if tokens.intersection({"decidido", "decisão", "decisao", "reunião", "reuniao", "ata"}):
            domain = "meetings"
            if intent != "technical":
                intent = "corporate_knowledge"
                confidence = max(confidence, 0.75)
            signals.append("meeting_terms")
        if tokens.intersection({"financeiro", "titulos", "títulos", "bancaria", "bancária", "conciliar", "conciliação", "conciliacao"}):
            domain = "finance"
            signals.append("finance_terms")
        if tokens.intersection(self.ROUTINE_ACTIVITY_TERMS):
            domain = "routine"
            signals.append("activity_terms")
        if tokens.intersection({"processo", "pop", "portal"}):
            domain = "processes"
            signals.append("process_terms")

        clarification_required = confidence < 0.5
        return {
            "intent": intent,
            "domain": domain,
            "confidence": round(confidence, 2),
            "signals": signals,
            "clarification_required": bool(clarification_required),
            "engine_version": self.ENGINE_VERSION,
        }

    def _record_interaction(
        self,
        *,
        question: str,
        payload: dict[str, Any],
        requested_scope: str,
        company_id: int | None,
        user_id: int,
        employee_id: int | None,
        understanding: dict[str, Any],
    ) -> KnowledgeInteraction:
        if not has_app_context():
            return SimpleNamespace(interaction_uuid=uuid.uuid4().hex)
        interaction = KnowledgeInteraction(
            interaction_uuid=uuid.uuid4().hex,
            company_id=company_id,
            user_id=user_id,
            employee_id=employee_id,
            requested_scope=requested_scope,
            knowledge_scope=str(payload.get("knowledge_scope") or ("company" if company_id else "product")),
            question=str(question or ""),
            normalized_question=self._normalize_question(question)[:600],
            answer_preview=str(payload.get("answer") or "")[:2000],
            understanding_json=dict(understanding or {}),
            query_plan_json=dict(payload.get("query_plan") or {}),
            citations_json=list(payload.get("citations") or []),
            actions_json=list(payload.get("actions") or []),
            warnings_json=list(payload.get("warnings") or []),
            engine_version=self.ENGINE_VERSION,
        )
        db.session.add(interaction)
        db.session.commit()
        return interaction

    @staticmethod
    def _normalize_question(question: str) -> str:
        text = str(question or "").strip().lower()
        text = re.sub(r"[^a-záàâãéêíóôõúç0-9]+", " ", text)
        return " ".join(text.split())

    def _direct_product_help(
        self,
        question: str,
        understanding: dict[str, Any],
    ) -> dict[str, Any] | None:
        normalized = self._normalize_question(question)
        tokens = set(normalized.split())
        if understanding.get("intent") != "product_help":
            return None
        if not tokens.intersection({"atividade", "atividades", "tarefa", "tarefas", "pendencias", "pendências", "pendencia"}):
            return None
        if not tokens.intersection({"meu", "minhas", "tenho", "ver", "vejo", "acompanhar", "consultar"}):
            return None

        answer = (
            "Para ver suas atividades:\n"
            "1. Abra **Meu Trabalho** no menu lateral.\n"
            "2. A tela já inicia na visão das suas atividades.\n"
            "3. Se necessário, use os filtros de empresa, status, prazo ou responsável.\n"
            "4. Para abrir uma atividade, clique no card ou na linha correspondente.\n\n"
            "Se você quiser ver atividades de processos, elas também aparecem no Meu Trabalho quando estiverem atribuídas a você."
        )
        return {
            "query_id": uuid.uuid4().hex,
            "mode": "answer",
            "knowledge_scope": "product",
            "answer": answer,
            "claims": [{"text": answer, "citations": []}],
            "citations": [],
            "warnings": [],
            "trust_signals": ["official"],
            "related_objects": [],
            "actions": [
                {
                    "kind": "open",
                    "label": "Abrir Meu Trabalho",
                    "target": "/my-work",
                    "canonical_uri": "/my-work",
                }
            ],
            "query_plan": {
                "query_kind": "direct_product_help",
                "knowledge_scope": "product",
                "company_id": None,
                "include_product": True,
                "source_types": ["product_help"],
                "strategies": ["deterministic_playbook"],
                "entities": ["activities"],
                "time": {"mode": "current", "from": None, "to": None},
                "filters": {},
                "limits": {"candidate_limit": 0, "answer_source_limit": 1},
            },
        }

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
