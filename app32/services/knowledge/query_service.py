from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import and_, case, exists, func, or_, select

from models import db
from models.knowledge import KnowledgeChunk, KnowledgeSource, KnowledgeSourceGrant


class KnowledgeQueryError(ValueError):
    """Erro de validação de uma consulta de conhecimento."""


class KnowledgeTenantContextError(KnowledgeQueryError):
    """Consulta corporativa sem empresa ativa confiável."""


@dataclass(frozen=True)
class KnowledgeQueryPlan:
    query_kind: str
    knowledge_scope: str
    company_id: int | None
    source_types: tuple[str, ...]
    strategies: tuple[str, ...]
    candidate_limit: int
    answer_source_limit: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_kind": self.query_kind,
            "knowledge_scope": self.knowledge_scope,
            "company_id": self.company_id,
            "source_types": list(self.source_types),
            "strategies": list(self.strategies),
            "entities": [],
            "time": {"mode": "current", "from": None, "to": None},
            "filters": {},
            "limits": {
                "candidate_limit": self.candidate_limit,
                "answer_source_limit": self.answer_source_limit,
            },
        }


class KnowledgeQueryService:
    """Planeja, recupera e compõe respostas citadas sem atravessar tenants."""

    MIN_QUERY_LENGTH = 3
    MAX_QUERY_LENGTH = 500
    MAX_SOURCE_LIMIT = 8
    MAX_CANDIDATE_LIMIT = 50
    _STOPWORDS = {
        "a",
        "as",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "eu",
        "o",
        "os",
        "para",
        "por",
        "que",
        "um",
        "uma",
    }

    def build_plan(
        self,
        question: str,
        *,
        company_id: int | None,
        source_types: Iterable[str] | None = None,
        answer_source_limit: int = 5,
        require_company: bool = True,
        query_kind: str = "answer",
    ) -> tuple[str, KnowledgeQueryPlan]:
        normalized_question = " ".join(str(question or "").split())
        if len(normalized_question) < self.MIN_QUERY_LENGTH:
            raise KnowledgeQueryError("A pergunta deve possuir ao menos 3 caracteres.")
        if len(normalized_question) > self.MAX_QUERY_LENGTH:
            raise KnowledgeQueryError("A pergunta excede o limite de 500 caracteres.")
        if require_company and company_id is None:
            raise KnowledgeTenantContextError(
                "Selecione uma empresa ativa antes de consultar conhecimento corporativo."
            )
        if company_id is not None and (
            isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0
        ):
            raise KnowledgeTenantContextError("Contexto de empresa inválido.")

        normalized_types = tuple(
            dict.fromkeys(
                str(item).strip().lower()
                for item in (source_types or ())
                if str(item).strip()
            )
        )
        source_limit = min(max(int(answer_source_limit), 1), self.MAX_SOURCE_LIMIT)
        scope = "company" if company_id is not None else "product"
        strategies = ("sql", "full_text")
        return normalized_question, KnowledgeQueryPlan(
            query_kind=query_kind,
            knowledge_scope=scope,
            company_id=company_id,
            source_types=normalized_types,
            strategies=strategies,
            candidate_limit=min(source_limit * 6, self.MAX_CANDIDATE_LIMIT),
            answer_source_limit=source_limit,
        )

    def search(
        self,
        question: str,
        *,
        company_id: int | None,
        source_types: Iterable[str] | None = None,
        limit: int = 5,
        require_company: bool = True,
        user_id: int | None = None,
        employee_id: int | None = None,
    ) -> dict[str, Any]:
        normalized_question, plan = self.build_plan(
            question,
            company_id=company_id,
            source_types=source_types,
            answer_source_limit=limit,
            require_company=require_company,
            query_kind="search",
        )
        terms = self._query_terms(normalized_question)
        rows = self._search_rows(
            normalized_question,
            terms=terms,
            plan=plan,
            user_id=user_id,
            employee_id=employee_id,
        )
        results = [
            self._serialize_hit(source, chunk, score=float(score or 0))
            for source, chunk, score in rows[: plan.answer_source_limit]
        ]
        return {
            "query_id": uuid.uuid4().hex,
            "mode": "search",
            "knowledge_scope": plan.knowledge_scope,
            "query_plan": plan.to_dict(),
            "results": results,
            "warnings": [] if results else ["Nenhuma evidência autorizada foi encontrada."],
        }

    def answer(
        self,
        question: str,
        *,
        company_id: int | None,
        source_types: Iterable[str] | None = None,
        limit: int = 5,
        require_company: bool = True,
        user_id: int | None = None,
        employee_id: int | None = None,
    ) -> dict[str, Any]:
        normalized_question, plan = self.build_plan(
            question,
            company_id=company_id,
            source_types=source_types,
            answer_source_limit=limit,
            require_company=require_company,
            query_kind="answer",
        )
        terms = self._query_terms(normalized_question)
        rows = self._search_rows(
            normalized_question,
            terms=terms,
            plan=plan,
            user_id=user_id,
            employee_id=employee_id,
        )
        hits = [
            self._serialize_hit(source, chunk, score=float(score or 0))
            for source, chunk, score in rows[: plan.answer_source_limit]
        ]
        if not hits:
            return self._abstention(plan)

        citations = []
        claims = []
        answer_parts = []
        actions = []
        trust_signals: list[str] = []
        for index, hit in enumerate(hits, start=1):
            citation_id = f"citation-{index}"
            citation = {
                "id": citation_id,
                "source_type": hit["source_type"],
                "source_ref": hit["source_ref"],
                "title": hit["title"],
                "source_span": hit["source_span"],
                "version": hit["version"],
                "valid_from": hit["valid_from"],
                "canonical_uri": hit["canonical_uri"],
            }
            citations.append(citation)
            claim_text = self._claim_text(hit["content"])
            claims.append({"text": claim_text, "citations": [citation_id]})
            answer_parts.append(f"{claim_text} [{index}]")
            if hit["authority_level"] not in trust_signals:
                trust_signals.append(hit["authority_level"])
            if hit["status"] not in trust_signals:
                trust_signals.append(hit["status"])
            if index == 1 and hit.get("navigation_target"):
                actions.append(
                    {
                        "kind": "open",
                        "label": "Abrir processo (Fluxo / POP)"
                        if hit["module_key"] == "processes"
                        else "Abrir no APP Versus",
                        "target": hit["navigation_target"],
                        "canonical_uri": hit["canonical_uri"],
                    }
                )

        return {
            "query_id": uuid.uuid4().hex,
            "mode": "answer",
            "knowledge_scope": plan.knowledge_scope,
            "answer": "\n\n".join(answer_parts),
            "trust_signals": trust_signals,
            "claims": claims,
            "citations": citations,
            "warnings": [],
            "related_objects": [],
            "actions": actions,
            "query_plan": plan.to_dict(),
        }

    def _search_rows(
        self,
        question: str,
        *,
        terms: tuple[str, ...],
        plan: KnowledgeQueryPlan,
        user_id: int | None,
        employee_id: int | None,
    ) -> list[tuple[KnowledgeSource, KnowledgeChunk, float]]:
        now = datetime.utcnow()
        grant_targets = [
            KnowledgeSourceGrant.grant_scope == "company",
        ]
        if user_id is not None:
            grant_targets.append(
                and_(
                    KnowledgeSourceGrant.grant_scope == "user",
                    KnowledgeSourceGrant.user_id == user_id,
                )
            )
        if employee_id is not None:
            grant_targets.append(
                and_(
                    KnowledgeSourceGrant.grant_scope == "employee",
                    KnowledgeSourceGrant.employee_id == employee_id,
                )
            )
        authorized_grant = exists(
            select(KnowledgeSourceGrant.id).where(
                KnowledgeSourceGrant.knowledge_source_id == KnowledgeSource.id,
                KnowledgeSourceGrant.company_id == plan.company_id,
                or_(*grant_targets),
            )
        )
        authority_rank = case(
            (KnowledgeSource.authority_level == "official", 3),
            (KnowledgeSource.authority_level == "internal", 2),
            else_=1,
        )
        query = (
            db.session.query(KnowledgeSource, KnowledgeChunk)
            .join(
                KnowledgeChunk,
                KnowledgeChunk.knowledge_source_id == KnowledgeSource.id,
            )
            .filter(
                KnowledgeSource.deleted_at.is_(None),
                KnowledgeSource.status.in_(("active", "published")),
                or_(KnowledgeSource.valid_from.is_(None), KnowledgeSource.valid_from <= now),
                or_(KnowledgeSource.valid_to.is_(None), KnowledgeSource.valid_to >= now),
                or_(
                    KnowledgeSource.knowledge_scope == "product",
                    (
                        (KnowledgeSource.knowledge_scope == "company")
                        & (KnowledgeSource.company_id == plan.company_id)
                        & authorized_grant
                    )
                    if plan.company_id is not None
                    else False,
                ),
            )
        )
        if plan.source_types:
            query = query.filter(KnowledgeSource.source_type.in_(plan.source_types))

        dialect_name = db.session.get_bind().dialect.name
        if dialect_name == "postgresql":
            ts_query = func.plainto_tsquery("portuguese", question)
            document_vector = func.to_tsvector("portuguese", KnowledgeChunk.content)
            score = func.ts_rank_cd(document_vector, ts_query).label("relevance")
            query = query.add_columns(score).filter(document_vector.op("@@")(ts_query))
        else:
            searchable = func.lower(
                func.coalesce(KnowledgeSource.title, "")
                + " "
                + func.coalesce(KnowledgeChunk.content, "")
            )
            matches = [searchable.like(f"%{term.lower()}%") for term in terms]
            score = sum(
                (case((match, 1.0), else_=0.0) for match in matches),
                0.0,
            ).label("relevance")
            query = query.add_columns(score).filter(or_(*matches))

        return (
            query.order_by(
                score.desc(),
                authority_rank.desc(),
                KnowledgeSource.source_updated_at.desc(),
                KnowledgeChunk.chunk_order.asc(),
            )
            .limit(plan.candidate_limit)
            .all()
        )

    @classmethod
    def _query_terms(cls, question: str) -> tuple[str, ...]:
        words = re.findall(r"[\wÀ-ÿ-]+", question.lower(), flags=re.UNICODE)
        terms = tuple(dict.fromkeys(word for word in words if word not in cls._STOPWORDS and len(word) > 1))
        return terms or tuple(dict.fromkeys(word for word in words if len(word) > 1))

    @staticmethod
    def _claim_text(content: str) -> str:
        normalized = " ".join(str(content or "").replace("**", "").split())
        if len(normalized) <= 900:
            return normalized
        return normalized[:897].rstrip() + "..."

    @staticmethod
    def _serialize_hit(
        source: KnowledgeSource,
        chunk: KnowledgeChunk,
        *,
        score: float,
    ) -> dict[str, Any]:
        return {
            "source_type": source.source_type,
            "source_ref": source.source_ref,
            "title": source.title,
            "content": chunk.content,
            "source_span": chunk.source_span or chunk.section_key,
            "version": source.version,
            "valid_from": source.valid_from.isoformat() if source.valid_from else None,
            "canonical_uri": source.canonical_uri,
            "authority_level": source.authority_level,
            "status": source.status,
            "module_key": source.module_key,
            "route_key": source.route_key,
            "navigation_target": source.navigation_target,
            "score": round(score, 6),
        }

    @staticmethod
    def _abstention(plan: KnowledgeQueryPlan) -> dict[str, Any]:
        return {
            "query_id": uuid.uuid4().hex,
            "mode": "answer",
            "knowledge_scope": plan.knowledge_scope,
            "answer": (
                "Não encontrei evidência autorizada suficiente para responder com segurança."
            ),
            "trust_signals": [],
            "claims": [],
            "citations": [],
            "warnings": ["knowledge_gap"],
            "related_objects": [],
            "actions": [],
            "query_plan": plan.to_dict(),
        }
