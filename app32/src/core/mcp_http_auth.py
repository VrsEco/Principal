from __future__ import annotations

import json
import os
import secrets
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Mapping
from urllib.parse import urlencode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

try:  # pragma: no cover - dependência opcional em ambiente de teste
    from mcp.server.auth.provider import AccessToken, OAuthAuthorizationServerProvider, TokenVerifier
    from mcp.server.auth.settings import AuthSettings
except ImportError:  # pragma: no cover
    @dataclass(frozen=True)
    class AccessToken:  # type: ignore[no-redef]
        token: str
        client_id: str
        scopes: list[str]
        resource: str | None = None

    @dataclass(frozen=True)
    class AuthSettings:  # type: ignore[no-redef]
        issuer_url: str
        service_documentation_url: str | None = None
        required_scopes: list[str] = field(default_factory=list)
        resource_server_url: str | None = None

    OAuthAuthorizationServerProvider = object  # type: ignore[assignment]
    TokenVerifier = object  # type: ignore[assignment]


HTTP_CONTEXT_HEADER_MAP = {
    "user_id": "x-app32-user-id",
    "company_id": "x-app32-company-id",
    "fallback_role": "x-app32-fallback-role",
    "thread_id": "x-app32-thread-id",
    "runtime_profile": "x-app32-runtime-profile",
    "actor_type": "x-app32-actor-type",
}

McpSurface = str


def normalize_surface(surface: McpSurface | str) -> str:
    normalized = str(surface).strip().lower()
    if normalized not in {"user", "admin", "analytics", "ops"}:
        raise ValueError(f"Surface MCP inválida: {surface!r}")
    return normalized


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _env_flag(name: str, default: bool = False) -> bool:
    value = str(os.environ.get(name, "")).strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class App32McpHttpIdentity:
    token: str
    user_id: int | None
    company_id: int | None
    fallback_role: str
    allowed_surfaces: tuple[str, ...]
    scopes: tuple[str, ...] = ("mcp:access",)
    client_id: str = "app32-mcp-internal"
    metadata: dict[str, Any] = field(default_factory=dict)

    def allows_surface(self, surface: McpSurface | str) -> bool:
        normalized = normalize_surface(surface)
        allowed = {value.strip().lower() for value in self.allowed_surfaces if str(value).strip()}
        return not allowed or normalized in allowed or "*" in allowed


@dataclass(frozen=True)
class App32OAuthPreparation:
    enabled: bool
    issuer_url: str | None
    service_documentation_url: str | None
    resource_server_url: str | None


_http_identity_ctx: ContextVar[App32McpHttpIdentity | None] = ContextVar("app32_mcp_http_identity", default=None)
_http_request_ctx: ContextVar[dict[str, Any] | None] = ContextVar("app32_mcp_http_request_context", default=None)


def set_http_request_context(identity: App32McpHttpIdentity, payload: Mapping[str, Any]) -> tuple[Any, Any]:
    identity_token = _http_identity_ctx.set(identity)
    request_token = _http_request_ctx.set(dict(payload))
    return identity_token, request_token


def reset_http_request_context(tokens: tuple[Any, Any]) -> None:
    identity_token, request_token = tokens
    _http_identity_ctx.reset(identity_token)
    _http_request_ctx.reset(request_token)


def get_http_request_identity() -> App32McpHttpIdentity | None:
    return _http_identity_ctx.get()


def get_http_request_context() -> dict[str, Any] | None:
    return _http_request_ctx.get()


def _single_token_config() -> dict[str, Any]:
    token = _coerce_str(os.environ.get("APP32_MCP_HTTP_TOKEN"))
    if not token:
        return {}
    return {
        token: {
            "user_id": os.environ.get("APP32_MCP_USER_ID"),
            "company_id": os.environ.get("APP32_MCP_COMPANY_ID"),
            "fallback_role": os.environ.get("APP32_MCP_FALLBACK_ROLE") or "colaborador",
            "allowed_surfaces": [value.strip() for value in (os.environ.get("APP32_MCP_HTTP_ALLOWED_SURFACES") or "*").split(",") if value.strip()],
            "scopes": ["mcp:access"],
            "client_id": os.environ.get("APP32_MCP_HTTP_CLIENT_ID") or "app32-mcp-internal",
        }
    }


def _multi_token_config() -> dict[str, Any]:
    raw = _coerce_str(os.environ.get("APP32_MCP_HTTP_TOKENS_JSON"))
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - proteção defensiva
        raise ValueError("APP32_MCP_HTTP_TOKENS_JSON inválido.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("APP32_MCP_HTTP_TOKENS_JSON deve ser um objeto token -> contexto.")
    return parsed


@lru_cache(maxsize=1)
def load_http_token_registry() -> dict[str, App32McpHttpIdentity]:
    registry: dict[str, App32McpHttpIdentity] = {}
    merged = {}
    merged.update(_multi_token_config())
    merged.update(_single_token_config())

    for token, config in merged.items():
        if not isinstance(config, Mapping):
            continue
        allowed_surfaces_raw = config.get("allowed_surfaces") or config.get("surfaces") or ["*"]
        if isinstance(allowed_surfaces_raw, str):
            allowed_surfaces = tuple(
                value.strip().lower()
                for value in allowed_surfaces_raw.split(",")
                if value.strip()
            ) or ("*",)
        else:
            allowed_surfaces = tuple(
                str(value).strip().lower()
                for value in allowed_surfaces_raw
                if str(value).strip()
            ) or ("*",)

        scopes_raw = config.get("scopes") or ["mcp:access"]
        if isinstance(scopes_raw, str):
            scopes = tuple(value.strip() for value in scopes_raw.split(",") if value.strip()) or ("mcp:access",)
        else:
            scopes = tuple(str(value).strip() for value in scopes_raw if str(value).strip()) or ("mcp:access",)

        registry[str(token)] = App32McpHttpIdentity(
            token=str(token),
            user_id=_coerce_optional_int(config.get("user_id")),
            company_id=_coerce_optional_int(config.get("company_id")),
            fallback_role=_coerce_str(config.get("fallback_role")) or "colaborador",
            allowed_surfaces=allowed_surfaces,
            scopes=scopes,
            client_id=_coerce_str(config.get("client_id")) or "app32-mcp-internal",
            metadata={
                "subject": _coerce_str(config.get("subject")),
                "description": _coerce_str(config.get("description")),
            },
        )
    return registry


def _resolve_db_backed_identity(
    request: Request | None,
    *,
    token: str,
    surface: McpSurface | str,
) -> App32McpHttpIdentity | None:
    company_id = None
    fallback_role_override = None
    client_name = None
    if request is not None:
        company_id = _coerce_optional_int(
            _coerce_str(request.headers.get(HTTP_CONTEXT_HEADER_MAP["company_id"]) or request.query_params.get("company_id"))
        )
        fallback_role_override = _coerce_str(
            _coerce_str(request.headers.get(HTTP_CONTEXT_HEADER_MAP["fallback_role"]) or request.query_params.get("fallback_role"))
        )
        client_name = _coerce_str(
            request.headers.get("x-app32-client-name")
            or request.headers.get("x-client-name")
            or request.headers.get("user-agent")
        )

    from services.user_mcp_token_service import user_mcp_token_service

    resolved = user_mcp_token_service.resolve_for_http_request(
        token=token,
        surface=normalize_surface(surface),
        company_id=company_id,
        client_name=client_name,
    )
    if resolved is None:
        return None
    return App32McpHttpIdentity(
        token=token,
        user_id=resolved.user_id,
        company_id=resolved.company_id,
        fallback_role=fallback_role_override or resolved.fallback_role,
        allowed_surfaces=resolved.allowed_surfaces,
        scopes=("mcp:access",),
        client_id="app32-mcp-user-token",
        metadata={
            "subject": resolved.subject,
            "client_name": resolved.client_name,
            "user_mcp_token_id": resolved.token_record_id,
        },
    )


class App32MCPTokenVerifier(TokenVerifier):
    def __init__(self, *, surface: McpSurface | str):
        self.surface = normalize_surface(surface)

    async def verify_token(self, token: str) -> AccessToken | None:
        identity = load_http_token_registry().get(token) or _resolve_db_backed_identity(
            None,
            token=token,
            surface=self.surface,
        )
        if identity is None or not identity.allows_surface(self.surface):
            return None
        return AccessToken(
            token=identity.token,
            client_id=identity.client_id,
            scopes=list(identity.scopes),
            resource=f"app32:{self.surface}",
        )


def extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None
    if not auth_header.lower().startswith("bearer "):
        return None
    return auth_header[7:].strip() or None


def _allow_context_override() -> bool:
    return _env_flag("APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE", default=False)


def _resolve_override_value(
    request: Request,
    *,
    query_param: str,
    header_name: str,
) -> str | None:
    if not _allow_context_override():
        return None
    return _coerce_str(request.headers.get(header_name) or request.query_params.get(query_param))


def resolve_request_identity(request: Request, *, surface: McpSurface | str) -> App32McpHttpIdentity | None:
    token = extract_bearer_token(request)
    if not token:
        return None
    identity = load_http_token_registry().get(token)
    if identity is None:
        return _resolve_db_backed_identity(request, token=token, surface=surface)
    if identity is None or not identity.allows_surface(surface):
        return None

    user_id = _coerce_optional_int(
        _resolve_override_value(request, query_param="user_id", header_name=HTTP_CONTEXT_HEADER_MAP["user_id"])
    )
    company_id = _coerce_optional_int(
        _resolve_override_value(request, query_param="company_id", header_name=HTTP_CONTEXT_HEADER_MAP["company_id"])
    )
    fallback_role = _coerce_str(
        _resolve_override_value(
            request,
            query_param="fallback_role",
            header_name=HTTP_CONTEXT_HEADER_MAP["fallback_role"],
        )
    )

    return App32McpHttpIdentity(
        token=identity.token,
        user_id=user_id if user_id is not None else identity.user_id,
        company_id=company_id if company_id is not None else identity.company_id,
        fallback_role=fallback_role or identity.fallback_role,
        allowed_surfaces=identity.allowed_surfaces,
        scopes=identity.scopes,
        client_id=identity.client_id,
        metadata=dict(identity.metadata),
    )


def resolve_request_context_payload(request: Request, *, surface: McpSurface | str) -> dict[str, Any]:
    identity = resolve_request_identity(request, surface=surface)
    if identity is None:
        return {}

    thread_id = _coerce_str(
        _resolve_override_value(request, query_param="thread_id", header_name=HTTP_CONTEXT_HEADER_MAP["thread_id"])
    )
    runtime_profile = _coerce_str(
        _resolve_override_value(request, query_param="runtime_profile", header_name=HTTP_CONTEXT_HEADER_MAP["runtime_profile"])
    )
    actor_type = _coerce_str(
        _resolve_override_value(request, query_param="actor_type", header_name=HTTP_CONTEXT_HEADER_MAP["actor_type"])
    )

    return {
        "user_id": identity.user_id,
        "company_id": identity.company_id,
        "fallback_role": identity.fallback_role,
        "surface": normalize_surface(surface),
        "transport": "streamable_http",
        "client": "claude_remote_connector",
        "thread_id": thread_id,
        "runtime_profile": runtime_profile,
        "actor_type": actor_type,
        "client_id": identity.client_id,
        "token_subject": identity.metadata.get("subject"),
    }


class App32MCPRequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, surface: McpSurface | str):
        super().__init__(app)
        self.surface = normalize_surface(surface)

    async def dispatch(self, request: Request, call_next):
        identity = resolve_request_identity(request, surface=self.surface)
        if identity is None:
            return JSONResponse({"error": "unauthorized", "detail": "Bearer token inválido ou ausente."}, status_code=401)

        if identity.user_id is None or identity.company_id is None:
            return JSONResponse(
                {
                    "error": "invalid_context",
                    "detail": "Token MCP sem user_id/company_id associado. Configure APP32_MCP_HTTP_TOKENS_JSON ou APP32_MCP_HTTP_TOKEN.",
                },
                status_code=403,
            )

        payload = resolve_request_context_payload(request, surface=self.surface)
        tokens = set_http_request_context(identity, payload)
        try:
            return await call_next(request)
        finally:
            reset_http_request_context(tokens)


def build_oauth_preparation(base_url: str | None = None) -> App32OAuthPreparation:
    issuer_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_ISSUER_URL"))
    resource_server_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_RESOURCE_SERVER_URL"))
    service_documentation_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_DOCS_URL"))

    normalized_base = _coerce_str(base_url or os.environ.get("APP32_MCP_PUBLIC_BASE_URL"))
    if issuer_url is None and normalized_base:
        issuer_url = normalized_base.rstrip("/") + "/oauth"
    if resource_server_url is None and normalized_base:
        resource_server_url = normalized_base.rstrip("/")

    enabled = bool(_env_flag("APP32_MCP_HTTP_ENABLE_OAUTH", default=False) and issuer_url and resource_server_url)
    return App32OAuthPreparation(
        enabled=enabled,
        issuer_url=issuer_url,
        service_documentation_url=service_documentation_url,
        resource_server_url=resource_server_url,
    )


def build_auth_settings(base_url: str | None = None) -> AuthSettings | None:
    preparation = build_oauth_preparation(base_url=base_url)
    normalized_base = _coerce_str(base_url or os.environ.get("APP32_MCP_PUBLIC_BASE_URL"))
    issuer_url = preparation.issuer_url or normalized_base
    resource_server_url = preparation.resource_server_url or normalized_base
    if not issuer_url or not resource_server_url:
        return None
    return AuthSettings(
        issuer_url=issuer_url,
        service_documentation_url=preparation.service_documentation_url,
        required_scopes=["mcp:access"],
        resource_server_url=resource_server_url,
    )


class App32OAuthAuthorizationServerProvider(OAuthAuthorizationServerProvider):
    """
    Estrutura-base para futura evolução OAuth do MCP remoto.

    Nesta entrega o fluxo completo não é ativado em produção; a classe serve
    como contrato explícito para a próxima iteração, preservando a separação
    entre:
    - autenticação do conector Claude
    - associação de identidade Claude -> usuário APP32
    - emissão/revogação de access/refresh tokens
    """

    async def get_client(self, client_id: str):
        raise NotImplementedError("OAuth dinâmico ainda não implementado para o MCP remoto do APP32.")

    async def register_client(self, client_info):
        raise NotImplementedError("OAuth dinâmico ainda não implementado para o MCP remoto do APP32.")

    async def authorize(self, client, params):
        raise NotImplementedError("OAuth ainda não implementado. Utilize o modo MVP por token interno.")

    async def load_authorization_code(self, client, authorization_code):
        raise NotImplementedError("OAuth ainda não implementado. Utilize o modo MVP por token interno.")

    async def exchange_authorization_code(self, client, authorization_code):
        raise NotImplementedError("OAuth ainda não implementado. Utilize o modo MVP por token interno.")

    async def load_refresh_token(self, client, refresh_token):
        raise NotImplementedError("OAuth ainda não implementado. Utilize o modo MVP por token interno.")

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        raise NotImplementedError("OAuth ainda não implementado. Utilize o modo MVP por token interno.")

    async def revoke_token(self, token):
        raise NotImplementedError("OAuth ainda não implementado. Utilize o modo MVP por token interno.")


def build_internal_token_example(
    *,
    user_id: int,
    company_id: int,
    fallback_role: str = "colaborador",
    surfaces: tuple[str, ...] = ("user", "admin", "analytics"),
) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    return {
        token: {
            "user_id": user_id,
            "company_id": company_id,
            "fallback_role": fallback_role,
            "allowed_surfaces": list(surfaces),
            "scopes": ["mcp:access"],
            "client_id": f"app32-{company_id}-{user_id}",
        }
    }


def build_authorize_redirect_url(login_url: str, *, state: str, redirect_uri: str) -> str:
    query = urlencode({"state": state, "redirect_uri": redirect_uri})
    separator = "&" if "?" in login_url else "?"
    return f"{login_url}{separator}{query}"


def make_oauth_not_ready_response() -> Response:
    return JSONResponse(
        {
            "error": "oauth_not_ready",
            "detail": "A camada OAuth do MCP remoto ainda não foi concluída. Use o modo MVP por token interno para testes controlados.",
        },
        status_code=501,
    )


def make_oauth_not_ready_redirect(login_url: str, *, state: str, redirect_uri: str) -> Response:
    return RedirectResponse(build_authorize_redirect_url(login_url, state=state, redirect_uri=redirect_uri))
