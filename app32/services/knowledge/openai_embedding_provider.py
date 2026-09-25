from __future__ import annotations

import logging
import os
from typing import Callable, Mapping, Sequence

from services.knowledge.embedding_usage import estimate_tokens
from services.knowledge.retrieval_strategy import KNOWLEDGE_EMBEDDING_DIMENSIONS, VectorRetrievalConfig

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "text-embedding-3-small"  # 1536 dimensões, igual à projeção pgvector
MAX_BATCH = 64
API_KEY_ENV = "OPENAI_API_KEY"
# Chave dedicada ao conhecimento, para um projeto do provedor com limite mensal próprio. Quando
# definida, tem precedência sobre `OPENAI_API_KEY` (que outras funções do app podem estar usando).
DEDICATED_API_KEY_ENV = "KNOWLEDGE_OPENAI_API_KEY"
# Limites explícitos: a consulta do usuário não pode esperar minutos pelo provedor. Falha => busca textual.
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MAX_RETRIES = 1


class OpenAIEmbeddingProvider:
    """Adapter de embeddings OpenAI. Só é criado em runtime com flag, modelo e chave presentes.

    A chave vem somente do ambiente: `KNOWLEDGE_OPENAI_API_KEY` (dedicada) ou, na falta dela,
    `OPENAI_API_KEY` lida pelo SDK. Nunca é logada nem persistida. O tráfego é sempre explícito:
    cada chamada envia texto à OpenAI e devolve o uso real de tokens para o ledger de consumo.
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        client=None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self._client = client
        self._timeout = timeout
        self._max_retries = max_retries
        self._api_key = api_key or None
        self.last_tokens: int = 0
        self.last_estimated: bool = True

    def _sdk(self):
        if self._client is None:
            from openai import OpenAI  # import tardio: sem SDK/chave nada é chamado

            options: dict = {"timeout": self._timeout, "max_retries": self._max_retries}
            if self._api_key:
                options["api_key"] = self._api_key
            self._client = OpenAI(**options)
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


def resolve_app_openai_key() -> str | None:
    """Chave OpenAI configurada na tela de integrações do app (serviço `ai`), a mesma do restante do app.

    Sem contexto de aplicação/banco (ou sem chave) devolve `None`; nunca levanta nem loga a chave.
    """

    try:
        from utils.integration_settings import resolve_openai_api_key

        return str(resolve_openai_api_key() or "").strip() or None
    except Exception:  # noqa: BLE001 - sem app/banco não há chave; a recuperação cai para busca textual
        logger.debug("knowledge embeddings: chave das integrações indisponível", exc_info=True)
        return None


def resolve_embedding_api_key(
    environ: Mapping[str, str] | None = None,
    *,
    app_key_resolver: Callable[[], str | None] | None = None,
) -> tuple[bool, str | None]:
    """Escolhe a chave dos embeddings: `(há_chave, chave_explícita)`.

    Ordem: `KNOWLEDGE_OPENAI_API_KEY` (dedicada), a chave das integrações do app (serviço `ai`, a
    mesma que o restante do app usa) e, por fim, `OPENAI_API_KEY` (aí a chave explícita é `None` e o
    SDK a lê sozinho). A consulta às integrações só ocorre sem chave dedicada.
    """

    env = os.environ if environ is None else environ
    dedicated = str(env.get(DEDICATED_API_KEY_ENV, "")).strip()
    if dedicated:
        return True, dedicated
    app_key = (app_key_resolver or resolve_app_openai_key)()
    if app_key:
        return True, app_key
    return bool(str(env.get(API_KEY_ENV, "")).strip()), None


def build_default_embedding_provider(
    environ: Mapping[str, str] | None = None,
    *,
    app_key_resolver: Callable[[], str | None] | None = None,
) -> OpenAIEmbeddingProvider | None:
    """Provedor de runtime a partir do ambiente; `None` (busca textual) se algo faltar.

    Exige, juntos: flag ligada, modelo, versão e geração configurados e uma chave (ver
    `resolve_embedding_api_key`). As integrações só são consultadas com tudo pronto. Nada é
    chamado aqui; o SDK só é criado na primeira consulta.
    """

    env = os.environ if environ is None else environ
    config = VectorRetrievalConfig.from_env(env)
    if not config.ready or config.embedding is None:
        return None
    available, api_key = resolve_embedding_api_key(env, app_key_resolver=app_key_resolver)
    if not available:
        return None
    return OpenAIEmbeddingProvider(model=config.embedding.model, api_key=api_key)


__all__ = [
    "API_KEY_ENV",
    "DEDICATED_API_KEY_ENV",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_BATCH",
    "OpenAIEmbeddingProvider",
    "build_default_embedding_provider",
    "resolve_app_openai_key",
    "resolve_embedding_api_key",
]
