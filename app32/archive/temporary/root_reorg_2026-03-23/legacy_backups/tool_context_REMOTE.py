from contextvars import ContextVar
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class SapiensIdentity:
    user_id: Optional[int] = None
    company_id: Optional[int] = None
    employee_id: Optional[int] = None
    channel: str = "web"  # web, telegram, instagram, whatsapp, email
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Contexto global para a thread de execução do Agente
_identity_ctx: ContextVar[SapiensIdentity] = ContextVar('sapiens_identity', default=SapiensIdentity())

def set_sapiens_context(
    user_id: Optional[int] = None,
    company_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    channel: str = "web",
    thread_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Define a identidade ativa para a execução atual do Agente (@ARQUITETO)."""
    identity = SapiensIdentity(
        user_id=user_id,
        company_id=company_id,
        employee_id=employee_id,
        channel=channel,
        thread_id=thread_id,
        metadata=metadata
    )
    return _identity_ctx.set(identity)

def get_sapiens_context() -> SapiensIdentity:
    """Recupera a identidade ativa no contexto atual."""
    return _identity_ctx.get()

def reset_sapiens_context(token):
    """Reseta o contexto de identidade (@ARQUITETO)."""
    _identity_ctx.reset(token)

# Mantemos compatibilidade legacional por enquanto
active_user_id_ctx = ContextVar('active_user_id', default=None)
active_company_id_ctx = ContextVar('active_company_id', default=None)
