"""Autosserviço do usuário no mcp-versus: dados do PRÓPRIO usuário da sessão, nunca de outro.

Substitui, para o mcp-versus, ``update_user_contacts(user_id, ...)``: aquela ferramenta recebe o id do
usuário alvo do cliente e depende de checagem de papel no corpo. Aqui o alvo é sempre o usuário
autenticado da sessão; ``company_id`` é explícito para o grant ser validado pelo wrapper do MCP.
"""

from __future__ import annotations

from typing import Any, Optional

_MAX_CONTACT_LENGTH = 64


def _clean(value: Optional[str], field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} deve ser texto.")
    cleaned = value.strip()
    if len(cleaned) > _MAX_CONTACT_LENGTH:
        raise ValueError(f"{field} deve ter no máximo {_MAX_CONTACT_LENGTH} caracteres.")
    return cleaned


def update_own_contacts(user_id: int, whatsapp: Optional[str], telegram: Optional[str]) -> dict[str, Any]:
    """Atualiza WhatsApp e/ou Telegram do usuário ``user_id`` (o chamador passa SEMPRE o da sessão)."""
    from models import db
    from models.user import User

    whatsapp = _clean(whatsapp, "whatsapp")
    telegram = _clean(telegram, "telegram")
    if whatsapp is None and telegram is None:
        raise ValueError("Informe whatsapp e/ou telegram.")
    user = User.query.get(user_id)
    if user is None:
        raise ValueError("Usuário da sessão não encontrado.")
    if whatsapp is not None:
        user.whatsapp = whatsapp
    if telegram is not None:
        user.telegram = telegram
    db.session.commit()
    return {"updated": [name for name, value in (("whatsapp", whatsapp), ("telegram", telegram)) if value is not None]}


def register_self_service_mcp_tools(mcp: Any) -> None:
    @mcp.tool()
    def update_my_contacts_secure(
        company_id: int,
        whatsapp: Optional[str] = None,
        telegram: Optional[str] = None,
    ) -> dict[str, Any]:
        """Atualiza o WhatsApp e/ou o Telegram do PRÓPRIO usuário autenticado (nunca de outra pessoa)."""
        from src.core.mcp_session_actor import require_session_user_id

        return update_own_contacts(require_session_user_id(), whatsapp, telegram)
