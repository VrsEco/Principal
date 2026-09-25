from __future__ import annotations

from typing import Sequence

from services.knowledge.embedding_usage import estimate_tokens
from services.knowledge.retrieval_strategy import KNOWLEDGE_EMBEDDING_DIMENSIONS

DEFAULT_MODEL = "text-embedding-3-small"  # 1536 dimensões, igual à projeção pgvector
MAX_BATCH = 64


class OpenAIEmbeddingProvider:
    """Adapter de embeddings OpenAI. Nunca instanciado por padrão em produção.

    A chave vem somente do ambiente (`OPENAI_API_KEY`, lida pelo SDK); não é logada,
    persistida nem recebida por parâmetro. O tráfego é sempre explícito: cada chamada
    envia texto à OpenAI e devolve o uso real de tokens para o ledger de consumo.
    """

    def __init__(self, *, model: str = DEFAULT_MODEL, client=None) -> None:
        self.model = model
        self._client = client
        self.last_tokens: int = 0
        self.last_estimated: bool = True

    def _sdk(self):
        if self._client is None:
            from openai import OpenAI  # import tardio: sem SDK/chave nada é chamado

            self._client = OpenAI()
        return self._client

    def embed_many(self, texts: Sequence[str]) -> tuple[list[list[float]], int, bool]:
        """Vetores na ordem de entrada + tokens + se o total foi estimado."""

        if not texts:
            return [], 0, False
        if len(texts) > MAX_BATCH:
            raise ValueError(f"Lote acima de {MAX_BATCH} textos.")
        response = self._sdk().embeddings.create(model=self.model, input=list(texts))
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        if len(vectors) != len(texts) or any(
            len(vector) != KNOWLEDGE_EMBEDDING_DIMENSIONS for vector in vectors
        ):
            raise RuntimeError("Resposta de embeddings com formato inesperado.")
        usage = getattr(response, "usage", None)
        reported = getattr(usage, "total_tokens", None)
        estimated = reported is None
        tokens = sum(estimate_tokens(t) for t in texts) if estimated else int(reported)
        return vectors, tokens, estimated

    def __call__(self, text: str) -> list[float]:
        vectors, tokens, estimated = self.embed_many([text])
        self.last_tokens, self.last_estimated = tokens, estimated
        return vectors[0]


__all__ = ["DEFAULT_MODEL", "MAX_BATCH", "OpenAIEmbeddingProvider"]
