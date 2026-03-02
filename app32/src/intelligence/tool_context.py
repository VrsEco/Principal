from contextvars import ContextVar

# Contexto para Agente / Webhooks
active_user_id_ctx = ContextVar('active_user_id', default=None)
active_company_id_ctx = ContextVar('active_company_id', default=None)
