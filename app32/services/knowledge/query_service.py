from __future__ import annotations

import re
import uuid
import logging
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Callable, Iterable, Sequence

from sqlalchemy import and_, case, exists, func, or_, select

from models import db
from models.knowledge import KnowledgeChunk, KnowledgeSource, KnowledgeSourceGrant
from services.knowledge.retrieval_strategy import (
    DEFAULT_STRATEGIES,
    EvidenceOrigin,
    HybridRankingPolicy,
    STRATEGY_HYBRID,
    STRATEGY_VECTOR,
    VectorRetrievalConfig,
    resolve_strategies,
    vector_pilot_allows,
)


class KnowledgeQueryError(ValueError):
    """Erro de validação de uma consulta de conhecimento."""


class KnowledgeTenantContextError(KnowledgeQueryError):
    """Consulta corporativa sem empresa ativa confiável."""


@dataclass(frozen=True)
class KnowledgeQueryPlan:
    query_kind: str
    knowledge_scope: str
    company_id: int | None
    include_product: bool
    source_types: tuple[str, ...]
    strategies: tuple[str, ...]
    candidate_limit: int
    answer_source_limit: int
    requested_strategy: str = "full_text"
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_kind": self.query_kind,
            "knowledge_scope": self.knowledge_scope,
            "company_id": self.company_id,
            "include_product": self.include_product,
            "source_types": list(self.source_types),
            "strategies": list(self.strategies),
            "requested_strategy": self.requested_strategy,
            "fallback_reason": self.fallback_reason,
            "evidence_origin": EvidenceOrigin.RAG.value,
            "entities": [],
            "time": {"mode": "current", "from": None, "to": None},
            "filters": {},
            "limits": {
                "candidate_limit": self.candidate_limit,
                "answer_source_limit": self.answer_source_limit,
            },
        }


def authorized_universe_conditions(
    plan: KnowledgeQueryPlan,
    *,
    user_id: int | None,
    employee_id: int | None,
    now: datetime,
) -> list[Any]:
    """Universo autorizado (tenant, grants, status, vigência, coerência ACL).

    É a única definição de "o que pode ser recuperado": FTS e qualquer recuperação
    vetorial futura devem aplicá-la *antes* de calcular relevância/distância.
    Espera um SELECT com ``KnowledgeSource`` juntado a ``KnowledgeChunk``.
    """

    grant_targets = [KnowledgeSourceGrant.grant_scope == "company"]
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
    visibility_filters = []
    if plan.include_product:
        visibility_filters.append(KnowledgeSource.knowledge_scope == "product")
    if plan.company_id is not None:
        visibility_filters.append(
            (KnowledgeSource.knowledge_scope == "company")
            & (KnowledgeSource.company_id == plan.company_id)
            & authorized_grant
        )
    if not visibility_filters:
        visibility_filters.append(False)

    conditions = [
        KnowledgeSource.deleted_at.is_(None),
        KnowledgeSource.status.in_(("active", "published")),
        or_(KnowledgeSource.valid_from.is_(None), KnowledgeSource.valid_from <= now),
        or_(KnowledgeSource.valid_to.is_(None), KnowledgeSource.valid_to >= now),
        # Drift de tenant/escopo entre fonte e chunk falha fechado.
        KnowledgeChunk.knowledge_scope == KnowledgeSource.knowledge_scope,
        or_(
            and_(KnowledgeChunk.company_id.is_(None), KnowledgeSource.company_id.is_(None)),
            KnowledgeChunk.company_id == KnowledgeSource.company_id,
        ),
        or_(*visibility_filters),
    ]
    if plan.source_types:
        conditions.append(KnowledgeSource.source_type.in_(plan.source_types))
    return conditions


logger = logging.getLogger(__name__)

EmbeddingProvider = Callable[[str], Sequence[float]]
VectorFetcher = Callable[..., list[tuple[KnowledgeSource, KnowledgeChunk, float]]]

# Sentinela: `embedding_provider` omitido = resolver do ambiente; `None` explícito = sem provedor.
_FROM_ENV: Any = object()


class KnowledgeQueryService:
    """Planeja, recupera e compõe respostas citadas sem atravessar tenants."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = _FROM_ENV,
        vector_config: VectorRetrievalConfig | None = None,
        vector_fetcher: VectorFetcher | None = None,
        ranking_policy: HybridRankingPolicy | None = None,
    ) -> None:
        if embedding_provider is _FROM_ENV:
            # Import tardio: a fábrica só devolve provedor com flag, modelo e chave presentes;
            # caso contrário a recuperação é somente FTS (estado atual de produção).
            from services.knowledge.openai_embedding_provider import build_default_embedding_provider

            embedding_provider = build_default_embedding_provider()
        self._embedding_provider = embedding_provider
        self._vector_config = vector_config
        self._vector_fetcher = vector_fetcher
        self._ranking_policy = ranking_policy or HybridRankingPolicy()

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
        "faco",
        "faço",
        "o",
        "os",
        "para",
        "pra",
        "por",
        "que",
        "um",
        "uma",
        "ver",
    }

    def _default_strategy(
        self, company_id: int | None, vector_config: VectorRetrievalConfig | None
    ) -> str | None:
        """Estratégia quando o chamador não pede uma: híbrida só com tudo pronto, senão o padrão (FTS).

        Exige provedor de embeddings, flag + modelo/versão/geração e empresa no piloto (se houver
        lista). Qualquer falta mantém a busca textual, que é o comportamento atual de produção.
        """

        if self._embedding_provider is None:
            return None
        config = vector_config or self._vector_config or VectorRetrievalConfig.from_env()
        if not config.ready or not vector_pilot_allows(company_id):
            return None
        return STRATEGY_HYBRID

    def build_plan(
        self,
        question: str,
        *,
        company_id: int | None,
        source_types: Iterable[str] | None = None,
        answer_source_limit: int = 5,
        require_company: bool = True,
        query_kind: str = "answer",
        include_product: bool = True,
        strategy: str | None = None,
        vector_config: VectorRetrievalConfig | None = None,
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
        if strategy is None:
            strategy = self._default_strategy(company_id, vector_config)
        try:
            resolution = resolve_strategies(strategy, vector_config or self._vector_config)
        except ValueError as exc:
            raise KnowledgeQueryError(str(exc)) from exc
        strategies = resolution.strategies
        fallback_reason = resolution.fallback_reason
        if (
            fallback_reason is None
            and set(strategies) & {STRATEGY_VECTOR, STRATEGY_HYBRID}
            and self._embedding_provider is None
        ):
            strategies = DEFAULT_STRATEGIES
            fallback_reason = "embedding_provider_missing"
        return normalized_question, KnowledgeQueryPlan(
            query_kind=query_kind,
            knowledge_scope=scope,
            company_id=company_id,
            include_product=include_product,
            source_types=normalized_types,
            strategies=strategies,
            candidate_limit=min(source_limit * 6, self.MAX_CANDIDATE_LIMIT),
            answer_source_limit=source_limit,
            requested_strategy=resolution.requested,
            fallback_reason=fallback_reason,
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
        include_product: bool = True,
        strategy: str | None = None,
    ) -> dict[str, Any]:
        normalized_question, plan = self.build_plan(
            question,
            company_id=company_id,
            source_types=source_types,
            answer_source_limit=limit,
            require_company=require_company,
            query_kind="search",
            include_product=include_product,
            strategy=strategy,
        )
        terms = self._query_terms(normalized_question)
        rows, runtime_warnings = self._retrieve(
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
            "warnings": self._plan_warnings(plan)
            + runtime_warnings
            + ([] if results else ["Nenhuma evidência autorizada foi encontrada."]),
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
        include_product: bool = True,
        strategy: str | None = None,
    ) -> dict[str, Any]:
        normalized_question, plan = self.build_plan(
            question,
            company_id=company_id,
            source_types=source_types,
            answer_source_limit=limit,
            require_company=require_company,
            query_kind="answer",
            include_product=include_product,
            strategy=strategy,
        )
        terms = self._query_terms(normalized_question)
        rows, runtime_warnings = self._retrieve(
            normalized_question,
            terms=terms,
            plan=plan,
            user_id=user_id,
            employee_id=employee_id,
        )
        retrieved_hits = [
            self._serialize_hit(source, chunk, score=float(score or 0))
            for source, chunk, score in rows[: plan.answer_source_limit]
        ]
        hits = self._select_answer_hits(normalized_question, retrieved_hits)
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
                "evidence_origin": EvidenceOrigin.RAG.value,
            }
            citations.append(citation)
            claim_text = self._claim_text(hit["content"])
            claims.append({"text": claim_text, "citations": [citation_id]})
            answer_parts.append(f"{claim_text} [{index}]")
            if hit["authority_level"] not in trust_signals:
                trust_signals.append(hit["authority_level"])
            if hit["status"] not in trust_signals:
                trust_signals.append(hit["status"])
            if index == 1:
                actions.extend(self._navigation_actions(hit))

        return {
            "query_id": uuid.uuid4().hex,
            "mode": "answer",
            "knowledge_scope": plan.knowledge_scope,
            "answer": "\n\n".join(answer_parts),
            "trust_signals": trust_signals,
            "claims": claims,
            "citations": citations,
            "warnings": self._plan_warnings(plan) + runtime_warnings,
            "related_objects": [],
            "actions": actions,
            "query_plan": plan.to_dict(),
        }

    def _retrieve(
        self,
        question: str,
        *,
        terms: tuple[str, ...],
        plan: KnowledgeQueryPlan,
        user_id: int | None,
        employee_id: int | None,
    ) -> tuple[list[tuple[KnowledgeSource, KnowledgeChunk, float]], list[str]]:
        """FTS sempre; vetor só quando o plano o inclui, com recuo seguro para FTS."""

        fts_rows = self._search_rows(
            question, terms=terms, plan=plan, user_id=user_id, employee_id=employee_id
        )
        if not set(plan.strategies) & {STRATEGY_VECTOR, STRATEGY_HYBRID}:
            return fts_rows, []
        try:
            vector_rows = self._vector_rows(
                question, plan=plan, user_id=user_id, employee_id=employee_id
            )
        except Exception:  # noqa: BLE001 - nunca vazar detalhe do provedor/SQL ao chamador
            logger.warning("knowledge vector retrieval failed; using full_text", exc_info=True)
            return fts_rows, ["vector_retrieval_failed"]
        config = self._vector_config or VectorRetrievalConfig.from_env()
        return self._merge_hybrid(fts_rows, vector_rows, plan, min_similarity=config.min_similarity), []

    def _vector_rows(
        self,
        question: str,
        *,
        plan: KnowledgeQueryPlan,
        user_id: int | None,
        employee_id: int | None,
    ) -> list[tuple[KnowledgeSource, KnowledgeChunk, float]]:
        config = self._vector_config or VectorRetrievalConfig.from_env()
        if config.embedding is None or self._embedding_provider is None:
            raise KnowledgeQueryError("Recuperação vetorial não configurada.")
        query_embedding = self._embedding_provider(question)
        self._record_query_usage(question, plan, config.embedding, user_id)
        if self._vector_fetcher is not None:
            return list(
                self._vector_fetcher(
                    plan, config.embedding, query_embedding, user_id=user_id, employee_id=employee_id
                )
            )
        from services.knowledge.vector_retrieval import build_vector_candidates_statement

        if db.session.get_bind().dialect.name != "postgresql":
            raise KnowledgeQueryError("Recuperação vetorial exige PostgreSQL.")
        statement = build_vector_candidates_statement(
            plan,
            config.embedding,
            query_embedding,
            user_id=user_id,
            employee_id=employee_id,
            now=datetime.utcnow(),
        )
        return [(row[0], row[1], float(row[2] or 0)) for row in db.session.execute(statement)]

    def _record_query_usage(self, question, plan, spec, user_id) -> None:
        """Registra data/hora e tokens da consulta (sem o texto); best effort."""

        from services.knowledge.embedding_usage import estimate_tokens, record_usage_event

        provider = self._embedding_provider
        reported = getattr(provider, "last_tokens", None)
        estimated = bool(getattr(provider, "last_estimated", True)) if reported else True
        record_usage_event(
            kind="query",
            company_id=plan.company_id,
            user_id=user_id,
            model=spec.model,
            version=spec.version,
            index_generation=spec.index_generation,
            tokens=reported if reported else estimate_tokens(question),
            estimated=estimated,
        )

    def _merge_hybrid(
        self,
        fts_rows: list[tuple[KnowledgeSource, KnowledgeChunk, float]],
        vector_rows: list[tuple[KnowledgeSource, KnowledgeChunk, float]],
        plan: KnowledgeQueryPlan,
        *,
        min_similarity: float = 0.0,
    ) -> list[tuple[KnowledgeSource, KnowledgeChunk, float]]:
        """FTS primeiro; o vetor só resgata o que o FTS não trouxe.

        A avaliação A/B em produção mostrou que a soma ponderada piorava o FTS (trechos sem vetor
        ganhavam peso redistribuído e o vizinho mais próximo era devolvido sem limiar). Aqui a ordem
        do FTS é preservada e o vetor acrescenta apenas candidatos com similaridade >= limiar, do mais
        para o menos similar. Ambos vêm do mesmo universo já autorizado.
        """

        seen = {chunk.id for _, chunk, _ in fts_rows}
        rescued = []
        for source, chunk, similarity in sorted(vector_rows, key=lambda row: -float(row[2] or 0)):
            if chunk.id in seen or float(similarity or 0) < min_similarity:
                continue
            seen.add(chunk.id)
            rescued.append((source, chunk, float(similarity)))
        return [*fts_rows, *rescued][: plan.candidate_limit]
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
                *authorized_universe_conditions(
                    plan, user_id=user_id, employee_id=employee_id, now=now
                )
            )
        )

        dialect_name = db.session.get_bind().dialect.name
        if dialect_name == "postgresql":
            searchable_document = (
                func.coalesce(KnowledgeSource.title, "")
                + " "
                + func.coalesce(KnowledgeChunk.content, "")
            )
            document_vector = func.to_tsvector("portuguese", searchable_document)
            term_queries = [func.plainto_tsquery("portuguese", term) for term in terms]
            term_matches = [document_vector.op("@@")(term_query) for term_query in term_queries]
            matched_term_count = sum(
                (case((term_match, 1.0), else_=0.0) for term_match in term_matches),
                0.0,
            )
            text_rank = sum(
                (func.ts_rank_cd(document_vector, term_query) for term_query in term_queries),
                0.0,
            )
            score = (matched_term_count + (text_rank * 0.01)).label("relevance")
            query = query.add_columns(score).filter(or_(*term_matches))
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

    @staticmethod
    def _plan_warnings(plan: KnowledgeQueryPlan) -> list[str]:
        return [plan.fallback_reason] if plan.fallback_reason else []

    @classmethod
    def _query_terms(cls, question: str) -> tuple[str, ...]:
        words = re.findall(r"[\wÀ-ÿ-]+", question.lower(), flags=re.UNICODE)
        terms = tuple(dict.fromkeys(word for word in words if word not in cls._STOPWORDS and len(word) > 1))
        return terms or tuple(dict.fromkeys(word for word in words if len(word) > 1))

    @staticmethod
    def _claim_text(content: str) -> str:
        lines = [line.rstrip() for line in str(content or "").replace("\r\n", "\n").split("\n")]
        normalized = "\n".join(lines).strip()
        if len(normalized) <= 1200:
            return normalized
        return normalized[:1197].rstrip() + "..."

    @classmethod
    def _select_answer_hits(
        cls,
        question: str,
        hits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Mantém a resposta útil ao usuário sem misturar documentação técnica."""
        if not hits:
            return []
        technical_terms = {
            "api",
            "arquitetura",
            "endpoint",
            "mcp",
            "paper",
            "spec",
            "técnico",
            "técnica",
            "tool",
        }
        query_terms = set(cls._query_terms(question))
        if query_terms.isdisjoint(technical_terms):
            non_technical = [
                hit for hit in hits if hit.get("source_type") != "system_documentation"
            ]
            if non_technical:
                hits = non_technical
            else:
                hits = [
                    hit for hit in hits if not cls._looks_like_technical_source(hit)
                ]

        product_help = [hit for hit in hits if hit.get("source_type") == "product_help"]
        if product_help and hits[0].get("source_type") == "product_help":
            # Um manual oficial completo é mais claro que a concatenação de documentos.
            return [product_help[0]]
        return hits[:3]

    @staticmethod
    def _looks_like_technical_source(hit: dict[str, Any]) -> bool:
        text = " ".join(
            str(hit.get(field) or "").lower()
            for field in ("title", "source_ref", "content", "source_span")
        )
        technical_markers = (
            "paper",
            "spec",
            "mcp",
            "api",
            "cli/ia",
            "arquitetura",
            "sapiens on",
            "adapter",
            "migration",
            "runtime",
        )
        return any(marker in text for marker in technical_markers)

    @staticmethod
    def _navigation_actions(hit: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = hit.get("metadata") or {}
        configured = metadata.get("navigation_actions") or []
        actions: list[dict[str, Any]] = []
        for action in configured:
            label = str(action.get("label") or "").strip()
            target = str(action.get("target") or "").strip()
            if not label or not target:
                continue
            actions.append(
                {
                    "kind": "open",
                    "label": label,
                    "target": target,
                    "canonical_uri": hit["canonical_uri"],
                }
            )
        if actions or not hit.get("navigation_target"):
            return actions
        return [
            {
                "kind": "open",
                "label": "Abrir processo (Fluxo / POP)"
                if hit["module_key"] == "processes"
                else "Abrir no APP Versus",
                "target": hit["navigation_target"],
                "canonical_uri": hit["canonical_uri"],
            }
        ]

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
            "metadata": dict(source.metadata_json or {}),
            "evidence_origin": EvidenceOrigin.RAG.value,
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
            "warnings": ["knowledge_gap", *KnowledgeQueryService._plan_warnings(plan)],
            "related_objects": [],
            "actions": [],
            "query_plan": plan.to_dict(),
        }
