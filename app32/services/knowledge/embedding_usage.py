from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Sequence

from models import db
from models.knowledge import KnowledgeEmbeddingUsageEvent, KnowledgeIndexRun

logger = logging.getLogger(__name__)

PRICE_PER_MILLION_ENV = "KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD"
USAGE_KEY = "embedding_usage"


def estimate_tokens(text: str) -> int:
    """Estimativa conservadora (~4 caracteres/token) quando o provedor não informa uso."""

    return max(1, math.ceil(len(str(text or "")) / 4))


@dataclass
class EmbeddingUsage:
    """Consumo acumulado de embeddings de uma execução; nunca guarda texto."""

    requests: int = 0
    tokens: int = 0
    estimated: bool = False

    def add(self, tokens: int, *, estimated: bool) -> None:
        self.requests += 1
        self.tokens += max(0, int(tokens))
        self.estimated = self.estimated or estimated


class MeteredEmbeddingProvider:
    """Envolve um provedor `texto -> vetor` e contabiliza tokens.

    `tokens_of` (opcional) devolve o uso real informado pelo provedor para o último
    texto; sem ele, usa-se a estimativa e o registro é marcado como estimado.
    """

    def __init__(
        self,
        inner: Callable[[str], Sequence[float]],
        *,
        tokens_of: Callable[[str], int | None] | None = None,
    ) -> None:
        self._inner = inner
        self._tokens_of = tokens_of
        self.usage = EmbeddingUsage()
        self.last_tokens: int = 0
        self.last_estimated: bool = True

    def __call__(self, text: str) -> Sequence[float]:
        vector = self._inner(text)
        reported = self._tokens_of(text) if self._tokens_of else None
        self.last_estimated = reported is None
        self.last_tokens = estimate_tokens(text) if reported is None else int(reported)
        self.usage.add(self.last_tokens, estimated=self.last_estimated)
        return vector


def record_usage_event(
    *,
    kind: str,
    company_id: int | None,
    user_id: int | None,
    model: str,
    version: str,
    index_generation: int,
    tokens: int,
    estimated: bool,
    run_id: int | None = None,
    query_id: str | None = None,
    occurred_at: datetime | None = None,
) -> bool:
    """Grava um evento datado (UTC) em conexão própria; falha nunca quebra o chamador.

    Conexão separada da sessão: uma consulta de leitura não é commitada nem revertida
    por causa da medição.
    """

    if kind not in {"index", "query"}:
        raise ValueError("kind deve ser 'index' ou 'query'.")
    try:
        with db.engine.begin() as connection:
            connection.execute(
                KnowledgeEmbeddingUsageEvent.__table__.insert().values(
                    occurred_at=occurred_at or datetime.utcnow(),
                    company_id=company_id,
                    user_id=user_id,
                    kind=kind,
                    run_id=run_id,
                    query_id=query_id,
                    embedding_model=model,
                    embedding_version=version,
                    index_generation=int(index_generation),
                    tokens=max(0, int(tokens)),
                    estimated=bool(estimated),
                )
            )
        return True
    except Exception:  # noqa: BLE001 - medição é best effort
        logger.warning("knowledge embedding usage event not recorded", exc_info=True)
        return False


def record_embedding_usage(
    run_id: int,
    usage: EmbeddingUsage,
    *,
    model: str,
    version: str,
    index_generation: int,
) -> KnowledgeIndexRun:
    """Soma o consumo ao ledger da execução (empresa = `company_id` da própria execução)."""

    run = db.session.get(KnowledgeIndexRun, run_id)
    if run is None:
        raise RuntimeError(f"KnowledgeIndexRun não encontrado: {run_id}")
    metadata = dict(run.metadata_json or {})
    previous = dict(metadata.get(USAGE_KEY) or {})
    metadata[USAGE_KEY] = {
        "model": model,
        "version": version,
        "index_generation": int(index_generation),
        "requests": int(previous.get("requests", 0)) + usage.requests,
        "tokens": int(previous.get("tokens", 0)) + usage.tokens,
        "estimated": bool(previous.get("estimated")) or usage.estimated,
    }
    run.metadata_json = metadata  # reatribui: mutação in-place não é detectada em JSON
    db.session.commit()
    record_usage_event(
        kind="index",
        company_id=run.company_id,
        user_id=None,
        model=model,
        version=version,
        index_generation=index_generation,
        tokens=usage.tokens,
        estimated=usage.estimated,
        run_id=run_id,
    )
    logger.info(
        "knowledge embedding usage run_id=%s company_id=%s tokens=%s estimated=%s",
        run_id,
        run.company_id,
        usage.tokens,
        usage.estimated,
    )
    return run


def summarize_embedding_usage(
    *,
    company_id: int | None = None,
    since: datetime | None = None,
    price_per_million_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Consumo por empresa (`company_id` nulo = manual do produto, custo da plataforma).

    O custo só é calculado se o preço por milhão de tokens for informado
    (parâmetro ou `KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD`); não há preço fixo no código.
    """

    if price_per_million_usd is None:
        raw = os.getenv(PRICE_PER_MILLION_ENV, "").strip()
        try:
            price_per_million_usd = float(raw) if raw else None
        except ValueError:
            price_per_million_usd = None

    query = db.session.query(KnowledgeIndexRun)
    if company_id is not None:
        query = query.filter(KnowledgeIndexRun.company_id == company_id)
    if since is not None:
        query = query.filter(KnowledgeIndexRun.started_at >= since)

    totals: dict[int | None, dict[str, Any]] = {}
    for run in query.all():
        usage = (run.metadata_json or {}).get(USAGE_KEY)
        if not usage:
            continue
        entry = totals.setdefault(
            run.company_id,
            {"company_id": run.company_id, "runs": 0, "requests": 0, "tokens": 0, "estimated": False},
        )
        entry["runs"] += 1
        entry["requests"] += int(usage.get("requests", 0))
        entry["tokens"] += int(usage.get("tokens", 0))
        entry["estimated"] = entry["estimated"] or bool(usage.get("estimated"))

    rows = sorted(totals.values(), key=lambda item: -item["tokens"])
    for entry in rows:
        entry["estimated_cost_usd"] = (
            round(entry["tokens"] / 1_000_000 * price_per_million_usd, 6)
            if price_per_million_usd is not None
            else None
        )
    return rows


def query_usage_events(
    *,
    company_id: int | None = None,
    kind: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    price_per_million_usd: float | None = None,
    group_by_day: bool = True,
) -> list[dict[str, Any]]:
    """Consulta por empresa, tipo e intervalo de data/hora (UTC), agregada por dia."""

    if price_per_million_usd is None:
        raw = os.getenv(PRICE_PER_MILLION_ENV, "").strip()
        try:
            price_per_million_usd = float(raw) if raw else None
        except ValueError:
            price_per_million_usd = None
    query = db.session.query(KnowledgeEmbeddingUsageEvent)
    if company_id is not None:
        query = query.filter(KnowledgeEmbeddingUsageEvent.company_id == company_id)
    if kind is not None:
        query = query.filter(KnowledgeEmbeddingUsageEvent.kind == kind)
    if since is not None:
        query = query.filter(KnowledgeEmbeddingUsageEvent.occurred_at >= since)
    if until is not None:
        query = query.filter(KnowledgeEmbeddingUsageEvent.occurred_at < until)
    totals: dict[tuple, dict[str, Any]] = {}
    for event in query.order_by(KnowledgeEmbeddingUsageEvent.occurred_at).all():
        day = event.occurred_at.date().isoformat() if group_by_day else None
        key = (event.company_id, event.kind, day)
        entry = totals.setdefault(
            key,
            {
                "company_id": event.company_id,
                "kind": event.kind,
                "day": day,
                "requests": 0,
                "tokens": 0,
                "estimated": False,
                "first_at": event.occurred_at.isoformat(),
                "last_at": event.occurred_at.isoformat(),
            },
        )
        entry["requests"] += 1
        entry["tokens"] += int(event.tokens)
        entry["estimated"] = entry["estimated"] or bool(event.estimated)
        entry["last_at"] = event.occurred_at.isoformat()
    rows = list(totals.values())
    for entry in rows:
        entry["estimated_cost_usd"] = (
            round(entry["tokens"] / 1_000_000 * price_per_million_usd, 8)
            if price_per_million_usd is not None
            else None
        )
    return rows


__all__ = [
    "query_usage_events",
    "record_usage_event",
    "EmbeddingUsage",
    "MeteredEmbeddingProvider",
    "estimate_tokens",
    "record_embedding_usage",
    "summarize_embedding_usage",
]
