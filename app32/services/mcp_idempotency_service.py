"""Idempotência das mutações do mcp-versus (SPEC onda 2, seção 10).

Fluxo no runtime: ``lookup`` (antes da aprovação, para repetir sem nova aprovação) -> ``claim`` (depois da
autorização, reserva a chave) -> ``complete``/``fail`` (depois da execução). A reserva é protegida pela restrição
única ``(company_id, principal_id, tool_name, idempotency_key)``; duas chamadas simultâneas não executam juntas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError

from models import db
from models.mcp_idempotency import McpIdempotencyKey

KEY_TTL = timedelta(hours=24)
STALE_IN_PROGRESS = timedelta(minutes=10)
MAX_STORED_RESULT_BYTES = 256 * 1024


@dataclass(frozen=True)
class IdempotencyDecision:
    action: str  # proceed | replay | conflict | in_progress
    row_id: Optional[int] = None
    result: Optional[dict] = None


def _now() -> datetime:
    return datetime.utcnow()


def _scope(company_id: int, principal_id: Any, tool_name: str, key: str):
    return (
        McpIdempotencyKey.company_id == int(company_id),
        McpIdempotencyKey.principal_id == str(principal_id),
        McpIdempotencyKey.tool_name == tool_name,
        McpIdempotencyKey.idempotency_key == key,
    )


def _load(company_id, principal_id, tool_name, key) -> Optional[McpIdempotencyKey]:
    return McpIdempotencyKey.query.filter(*_scope(company_id, principal_id, tool_name, key)).first()


def _reusable(row: McpIdempotencyKey, now: datetime) -> bool:
    """Linha que pode ser retomada: expirada, falha ou reserva parada há muito tempo."""
    if row.expires_at <= now or row.status == "failed":
        return True
    return row.status == "in_progress" and row.updated_at <= now - STALE_IN_PROGRESS


def lookup(*, company_id: int, principal_id: Any, tool_name: str, key: str, payload_digest: str) -> IdempotencyDecision:
    """Consulta sem reservar: repete o resultado guardado, recusa reuso com outro payload ou segue."""
    row = _load(company_id, principal_id, tool_name, key)
    if row is None:
        return IdempotencyDecision("proceed")
    now = _now()
    if row.expires_at > now and row.payload_digest != payload_digest:
        return IdempotencyDecision("conflict", row.id)
    if row.status == "succeeded" and row.expires_at > now:
        return IdempotencyDecision("replay", row.id, dict(row.result or {}))
    if row.status == "in_progress" and not _reusable(row, now):
        return IdempotencyDecision("in_progress", row.id)
    return IdempotencyDecision("proceed", row.id)


def claim(*, company_id: int, principal_id: Any, tool_name: str, key: str, payload_digest: str) -> IdempotencyDecision:
    """Reserva a chave antes de executar. Quem perde a corrida recebe ``in_progress``."""
    now = _now()
    row = _load(company_id, principal_id, tool_name, key)
    if row is not None:
        if row.expires_at > now and row.payload_digest != payload_digest:
            return IdempotencyDecision("conflict", row.id)
        if row.status == "succeeded" and row.expires_at > now:
            return IdempotencyDecision("replay", row.id, dict(row.result or {}))
        if not _reusable(row, now):
            return IdempotencyDecision("in_progress", row.id)
        previous_status, previous_updated = row.status, row.updated_at
        updated = (
            McpIdempotencyKey.query.filter(
                McpIdempotencyKey.id == row.id,
                McpIdempotencyKey.status == previous_status,
                McpIdempotencyKey.updated_at == previous_updated,
            ).update(
                {
                    "status": "in_progress",
                    "payload_digest": payload_digest,
                    "result": None,
                    "created_at": now,
                    "updated_at": now,
                    "expires_at": now + KEY_TTL,
                },
                synchronize_session=False,
            )
        )
        db.session.commit()
        return IdempotencyDecision("proceed", row.id) if updated else IdempotencyDecision("in_progress", row.id)
    row = McpIdempotencyKey(
        company_id=int(company_id),
        principal_id=str(principal_id),
        tool_name=tool_name,
        idempotency_key=key,
        payload_digest=payload_digest,
        status="in_progress",
        created_at=now,
        updated_at=now,
        expires_at=now + KEY_TTL,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return IdempotencyDecision("in_progress")
    return IdempotencyDecision("proceed", row.id)


def _storable(result: Any) -> dict:
    if not isinstance(result, dict):
        result = {"success": True, "value": result}
    encoded = json.dumps(result, ensure_ascii=False, default=str)
    if len(encoded.encode("utf-8")) > MAX_STORED_RESULT_BYTES:
        return {"success": True, "replay_truncated": True, "note": "resultado grande demais para repetir; consulte o registro criado"}
    return json.loads(encoded)


def complete(row_id: int, result: Any) -> None:
    """Grava o resultado; resposta de falha de negócio (``success: False``) libera a chave para nova tentativa."""
    failed = isinstance(result, dict) and result.get("success") is False
    row = db.session.get(McpIdempotencyKey, row_id)
    if row is None:
        return
    row.status = "failed" if failed else "succeeded"
    row.result = None if failed else _storable(result)
    db.session.commit()


def fail(row_id: int) -> None:
    """A execução levantou exceção: libera a chave para nova tentativa com o mesmo payload."""
    db.session.rollback()
    row = db.session.get(McpIdempotencyKey, row_id)
    if row is None:
        return
    row.status = "failed"
    row.result = None
    db.session.commit()


def count_expired(older_than: timedelta = timedelta(0)) -> int:
    """Quantas linhas venceram há mais de ``older_than`` (leitura; usada no modo de simulação)."""
    return McpIdempotencyKey.query.filter(McpIdempotencyKey.expires_at <= _now() - older_than).count()


def purge_expired(limit: int = 1000, older_than: timedelta = timedelta(0)) -> int:
    """Remove linhas vencidas há mais de ``older_than`` (tarefa agendada; em lotes de ``limit``)."""
    cutoff = _now() - older_than
    ids = [r.id for r in McpIdempotencyKey.query.filter(McpIdempotencyKey.expires_at <= cutoff).limit(limit)]
    if not ids:
        return 0
    McpIdempotencyKey.query.filter(McpIdempotencyKey.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return len(ids)
