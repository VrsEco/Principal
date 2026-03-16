import logging
from typing import Any

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

DEFAULT_PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."
PRODUCTION_FIRST_INVESTIGATION_STEPS = (
    "Analisar primeiro no ambiente de produção.",
    "Comparar produção com desenvolvimento (código, banco, dependências e configuração).",
    "Se houver divergência, corrigir a divergência, fazer deploy e validar.",
    "Se não houver divergência, corrigir em desenvolvimento, validar e então fazer deploy.",
)


def is_api_like_request() -> bool:
    path = (request.path or "").lower()
    if path.startswith("/api/") or path.startswith("/webhook/"):
        return True
    if path.startswith("/health"):
        return True
    if request.blueprint in {"telegram", "whatsapp_webhook"}:
        return True
    if request.accept_mimetypes.best == "application/json":
        return True
    return bool(request.is_json)


def build_public_error_payload(
    *,
    message: str = DEFAULT_PUBLIC_ERROR_MESSAGE,
    success: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    payload = {"success": success, "message": message}
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


def build_public_error_response(
    *,
    message: str = DEFAULT_PUBLIC_ERROR_MESSAGE,
    status_code: int = 500,
    success: bool = False,
    **extra: Any,
):
    return jsonify(build_public_error_payload(message=message, success=success, **extra)), status_code


def log_exception_with_context(logger: logging.Logger, exc: Exception, *, context: str) -> None:
    from flask_login import current_user

    try:
        user_id = getattr(current_user, "id", None)
    except Exception:
        user_id = None

    logger.exception(
        "%s | method=%s path=%s user_id=%s remote_addr=%s error=%s",
        context,
        request.method,
        request.path,
        user_id,
        request.remote_addr,
        exc,
    )


def register_global_error_handlers(app) -> None:
    logger = logging.getLogger(__name__)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc):
        if isinstance(exc, HTTPException):
            return exc

        log_exception_with_context(logger, exc, context="Exceção não tratada")

        if is_api_like_request():
            return build_public_error_response()

        return DEFAULT_PUBLIC_ERROR_MESSAGE, 500
