from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

STRATEGY_SQL = "sql"
STRATEGY_FULL_TEXT = "full_text"
STRATEGY_VECTOR = "vector"
STRATEGY_RELATIONSHIP_GRAPH = "relationship_graph"
STRATEGY_HYBRID = "hybrid"

SUPPORTED_STRATEGIES = (
    STRATEGY_SQL,
    STRATEGY_FULL_TEXT,
    STRATEGY_VECTOR,
    STRATEGY_RELATIONSHIP_GRAPH,
    STRATEGY_HYBRID,
)
# FTS PostgreSQL permanece o caminho seguro e o único executado hoje.
DEFAULT_STRATEGIES = (STRATEGY_SQL, STRATEGY_FULL_TEXT)
_PENDING_STRATEGIES = (STRATEGY_VECTOR, STRATEGY_HYBRID)

# Consulta vetorial ligada ao QueryService, mas só executa com flag + modelo configurados
# E um provedor de embedding injetado (ausente em produção). Ensaio em pgvector pendente.
VECTOR_BACKEND_IMPLEMENTED = True

VECTOR_FLAG_ENV = "KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED"
EMBEDDING_MODEL_ENV = "KNOWLEDGE_EMBEDDING_MODEL"
EMBEDDING_VERSION_ENV = "KNOWLEDGE_EMBEDDING_VERSION"
INDEX_GENERATION_ENV = "KNOWLEDGE_EMBEDDING_INDEX_GENERATION"

# Dimensão fixada pela migration da projeção vetorial; trocar exige nova geração.
KNOWLEDGE_EMBEDDING_DIMENSIONS = 1536
EMBEDDINGS_TABLE = "knowledge_chunk_embeddings"


class EvidenceOrigin(str, Enum):
    """Origem de cada evidência; respostas híbridas nunca as misturam."""

    RAG = "rag"
    LIVE_MCP = "live_mcp"
    EXTERNAL = "external"


@dataclass(frozen=True)
class EmbeddingSpec:
    model: str
    version: str
    index_generation: int
    dimensions: int = KNOWLEDGE_EMBEDDING_DIMENSIONS


@dataclass(frozen=True)
class VectorRetrievalConfig:
    """Feature flag da recuperação vetorial. Nasce desligada e sem modelo."""

    enabled: bool = False
    embedding: EmbeddingSpec | None = None

    @property
    def ready(self) -> bool:
        return bool(self.enabled and self.embedding and VECTOR_BACKEND_IMPLEMENTED)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "VectorRetrievalConfig":
        env = os.environ if environ is None else environ
        enabled = str(env.get(VECTOR_FLAG_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}
        model = str(env.get(EMBEDDING_MODEL_ENV, "")).strip()
        version = str(env.get(EMBEDDING_VERSION_ENV, "")).strip()
        generation_raw = str(env.get(INDEX_GENERATION_ENV, "")).strip()
        if not (enabled and model and version and generation_raw.isdigit()):
            return cls(enabled=enabled, embedding=None)
        return cls(
            enabled=True,
            embedding=EmbeddingSpec(model=model, version=version, index_generation=int(generation_raw)),
        )


@dataclass(frozen=True)
class StrategyResolution:
    requested: str
    strategies: tuple[str, ...]
    fallback_reason: str | None = None


def resolve_strategies(
    requested: str | None,
    config: VectorRetrievalConfig | None = None,
) -> StrategyResolution:
    """Valida a estratégia pedida e recua para FTS quando o recurso não está pronto."""

    normalized = str(requested or STRATEGY_FULL_TEXT).strip().lower()
    if normalized not in SUPPORTED_STRATEGIES:
        raise ValueError(f"Estratégia de recuperação desconhecida: {normalized!r}.")
    if normalized in (STRATEGY_SQL, STRATEGY_FULL_TEXT):
        return StrategyResolution(normalized, DEFAULT_STRATEGIES)
    if normalized == STRATEGY_RELATIONSHIP_GRAPH:
        return StrategyResolution(normalized, DEFAULT_STRATEGIES, "relationship_graph_not_available")
    config = config or VectorRetrievalConfig.from_env()
    if not config.enabled:
        return StrategyResolution(normalized, DEFAULT_STRATEGIES, "vector_retrieval_disabled")
    if not config.ready:
        return StrategyResolution(normalized, DEFAULT_STRATEGIES, "vector_backend_pending")
    return StrategyResolution(normalized, (*DEFAULT_STRATEGIES, normalized))


@dataclass(frozen=True)
class HybridRankingPolicy:
    """Ranking explícito. Autorização, status e vigência são *gates* (filtro SQL
    anterior à busca), nunca pesos: um chunk não autorizado não chega ao ranking."""

    authority_weight: float = 0.25
    lexical_weight: float = 0.35
    vector_weight: float = 0.30
    recency_weight: float = 0.10

    def score(
        self,
        *,
        authority: float,
        lexical: float,
        vector_similarity: float | None,
        recency: float,
    ) -> float:
        """Todos os componentes normalizados em [0, 1]; sem vetor, o peso é redistribuído."""

        components = {
            "authority": (self.authority_weight, authority),
            "lexical": (self.lexical_weight, lexical),
            "recency": (self.recency_weight, recency),
        }
        if vector_similarity is not None:
            components["vector"] = (self.vector_weight, vector_similarity)
        total_weight = sum(weight for weight, _ in components.values())
        return sum(weight * min(max(value, 0.0), 1.0) for weight, value in components.values()) / total_weight


__all__ = [
    "DEFAULT_STRATEGIES",
    "EMBEDDINGS_TABLE",
    "EmbeddingSpec",
    "EvidenceOrigin",
    "HybridRankingPolicy",
    "KNOWLEDGE_EMBEDDING_DIMENSIONS",
    "STRATEGY_FULL_TEXT",
    "STRATEGY_HYBRID",
    "STRATEGY_RELATIONSHIP_GRAPH",
    "STRATEGY_SQL",
    "STRATEGY_VECTOR",
    "SUPPORTED_STRATEGIES",
    "StrategyResolution",
    "VECTOR_BACKEND_IMPLEMENTED",
    "VectorRetrievalConfig",
    "resolve_strategies",
]
