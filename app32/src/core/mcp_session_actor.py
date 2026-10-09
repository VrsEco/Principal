"""Ator da sessão MCP autenticada.

Em mutações, quem consta como autor, solicitante ou aprovador é SEMPRE o usuário da sessão OAuth:
nenhuma ferramenta aceita ``user_id``/``approver_user_id`` do cliente (contrato de mutações, regra M2).
"""

from __future__ import annotations

from typing import Optional

from src.core.mcp_http_auth import get_http_request_context


def session_user_id() -> Optional[int]:
    """Id do usuário da sessão MCP atual, ou ``None`` quando a sessão não o identifica."""
    raw = dict(get_http_request_context() or {}).get("user_id")
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def require_session_user_id() -> int:
    user_id = session_user_id()
    if user_id is None:
        raise PermissionError("Usuário autenticado não identificado para a operação MCP.")
    return user_id
