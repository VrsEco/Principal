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

from src.intelligence.security.mcp_channel_gate import McpChannelGateRequest, evaluate_mcp_channel_gate
from src.intelligence.security.oauth_token_verifier import (
    OAuthAccessTokenVerifier,
    OAuthTokenVerificationError,
    OAuthTokenVerifierSettings,
)
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec, normalize_runtime_profile


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
    # Só pode ser preenchido por um resolvedor de identidade confiável ou por
    # configuração server-side. Nunca é obtido de header, query ou payload MCP.
    principal_id: int | None = None
    subject_type: str = "USER"
    issuer: str | None = None
    subject: str | None = None
    auth_method: str | None = None
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


@dataclass(frozen=True)
class OAuthHttpIdentityResolution:
    """Resultado do adaptador OIDC antes da autorização por tenant.

    A resolução só transforma um JWT já verificado em um principal APP32
    previamente vinculado. A escolha da empresa continua no runtime MCP e é
    obrigatoriamente reavaliada pelo ``PrincipalCompanyGrant``.
    """

    identity: App32McpHttpIdentity | None
    status_code: int
    error: str | None = None
    detail: str | None = None

    @property
    def allowed(self) -> bool:
        return self.identity is not None


_http_identity_ctx: ContextVar[App32McpHttpIdentity | None] = ContextVar("app32_mcp_http_identity", default=None)
_http_request_ctx: ContextVar[dict[str, Any] | None] = ContextVar("app32_mcp_http_request_context", default=None)


def _infer_surface_from_request(request: Request) -> str | None:
    try:
        scope = getattr(request, "scope", {}) or {}
        root_path = _coerce_str(scope.get("root_path")) or ""
        path = _coerce_str(scope.get("path")) or ""
        candidate = f"{root_path.rstrip('/')}/{path.lstrip('/')}".strip("/") or path.strip("/") or root_path.strip("/")
        segments = [segment.strip().lower() for segment in candidate.split("/") if segment.strip()]
        if "mcp" in segments:
            mcp_index = segments.index("mcp")
            if mcp_index + 1 < len(segments):
                return normalize_surface(segments[mcp_index + 1])
        for segment in reversed(segments):
            if segment in {"user", "admin", "analytics", "ops"}:
                return normalize_surface(segment)
    except Exception:
        return None
    return None


def _get_current_mcp_server_request() -> Request | None:
    try:
        from mcp.server.lowlevel.server import request_ctx
    except Exception:
        return None

    try:
        current_context = request_ctx.get()
    except LookupError:
        return None
    except Exception:
        return None

    request = getattr(current_context, "request", None)
    return request if isinstance(request, Request) else None


def _resolve_identity_from_current_request(
    request: Request,
    *,
    preferred_surface: str | None = None,
) -> tuple[App32McpHttpIdentity | None, str | None]:
    candidate_surfaces: list[str] = []
    if preferred_surface:
        candidate_surfaces.append(preferred_surface)
    candidate_surfaces.extend(
        surface
        for surface in ("user", "admin", "analytics", "ops")
        if surface not in candidate_surfaces
    )

    for surface in candidate_surfaces:
        try:
            identity = resolve_request_identity(request, surface=surface)
        except Exception:
            identity = None
        if identity is not None:
            return identity, surface
    return None, None


def set_http_request_context(identity: App32McpHttpIdentity, payload: Mapping[str, Any]) -> tuple[Any, Any]:
    identity_token = _http_identity_ctx.set(identity)
    request_token = _http_request_ctx.set(dict(payload))
    return identity_token, request_token


def reset_http_request_context(tokens: tuple[Any, Any]) -> None:
    identity_token, request_token = tokens
    _http_identity_ctx.reset(identity_token)
    _http_request_ctx.reset(request_token)


def _resolve_identity_from_mcp_auth_context() -> tuple[App32McpHttpIdentity | None, str | None]:
    """Recupera identidade no task context do SDK MCP (inclusive streamable-http)."""
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        access_token = get_access_token()
    except Exception:
        access_token = None
    if access_token is None:
        return None, None

    token = _coerce_str(getattr(access_token, "token", None))
    resource = _coerce_str(getattr(access_token, "resource", None)) or ""
    if not token:
        return None, None
    resource_surface = resource.rsplit(":", 1)[-1].strip().lower() if ":" in resource else "user"
    try:
        surface = normalize_surface(resource_surface)
    except ValueError:
        surface = "user"
    identity = load_http_token_registry().get(token) or _resolve_db_backed_identity(
        None,
        token=token,
        surface=surface,
    )
    if identity is None or not identity.allows_surface(surface):
        return None, None
    return identity, surface


def get_http_request_identity() -> App32McpHttpIdentity | None:
    identity = _http_identity_ctx.get()
    if identity is not None:
        return identity

    auth_identity, _ = _resolve_identity_from_mcp_auth_context()
    if auth_identity is not None:
        return auth_identity

    request = _get_current_mcp_server_request()
    if request is None:
        return None

    identity, _ = _resolve_identity_from_current_request(
        request,
        preferred_surface=_infer_surface_from_request(request),
    )
    return identity


def get_http_request_context() -> dict[str, Any] | None:
    payload = _http_request_ctx.get()
    if payload:
        return payload

    auth_identity, auth_surface = _resolve_identity_from_mcp_auth_context()
    if auth_identity is not None and auth_surface is not None:
        return _build_identity_context_payload(auth_identity, surface=auth_surface)

    request = _get_current_mcp_server_request()
    if request is None:
        return payload

    scoped_payload = request.scope.get("app32_mcp_context")
    if isinstance(scoped_payload, Mapping) and scoped_payload:
        return dict(scoped_payload)

    identity, surface = _resolve_identity_from_current_request(
        request,
        preferred_surface=_infer_surface_from_request(request),
    )
    if identity is None or surface is None:
        return payload

    try:
        resolved = resolve_request_context_payload(request, surface=surface)
    except Exception:
        return payload
    return resolved or payload


def get_http_actor_role(default: str | None = None) -> str | None:
    """Retorna o papel-base autenticado sem confundi-lo com runtime ou harness."""
    context = dict(get_http_request_context() or {})
    role = _coerce_str(context.get("fallback_role")) or _coerce_str(default)
    return role.lower() if role else None


def _single_token_config() -> dict[str, Any]:
    token = _coerce_str(os.environ.get("APP32_MCP_HTTP_TOKEN"))
    if not token:
        return {}
    return {
        token: {
            "user_id": os.environ.get("APP32_MCP_USER_ID"),
            "company_id": os.environ.get("APP32_MCP_COMPANY_ID"),
            "principal_id": os.environ.get("APP32_MCP_PRINCIPAL_ID"),
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
            principal_id=_coerce_optional_int(config.get("principal_id")),
            subject_type=_coerce_str(config.get("subject_type")) or "USER",
            issuer=_coerce_str(config.get("issuer")),
            subject=_coerce_str(config.get("subject")),
            auth_method=_coerce_str(config.get("auth_method")) or "internal_bearer",
            fallback_role=_coerce_str(config.get("fallback_role")) or "colaborador",
            allowed_surfaces=allowed_surfaces,
            scopes=scopes,
            client_id=_coerce_str(config.get("client_id")) or "app32-mcp-internal",
            metadata={
                "description": _coerce_str(config.get("description")),
                "mcp_enabled": True,
                "training_completed": True,
            },
        )
    return registry


def _oauth_enabled_surfaces() -> frozenset[str]:
    """Retorna a coorte OIDC explícita; ausência nunca muda o legado.

    Não há inferência por token, header ou rota: uma surface só troca de
    contrato quando o operador a inclui nesta allowlist server-side.
    """

    raw = _coerce_str(os.environ.get("APP32_MCP_OIDC_ENABLED_SURFACES"))
    if not raw:
        return frozenset()
    surfaces: set[str] = set()
    for value in raw.split(","):
        candidate = value.strip().lower()
        if not candidate:
            continue
        surfaces.add(normalize_surface(candidate))
    return frozenset(surfaces)


def oauth_transport_enabled_for_surface(surface: McpSurface | str, *, forced: bool | None = None) -> bool:
    """Indica se uma surface está em coorte OAuth; default é sempre legado."""

    if forced is not None:
        return forced
    return bool(
        _env_flag("APP32_MCP_HTTP_ENABLE_OAUTH", default=False)
        and normalize_surface(surface) in _oauth_enabled_surfaces()
    )


def _principal_grant_gate_enabled() -> bool:
    return _env_flag("APP32_MCP_USE_PRINCIPAL_GRANTS", default=False)


@lru_cache(maxsize=1)
def load_oauth_access_token_verifier() -> OAuthAccessTokenVerifier:
    """Monta o verifier somente para a coorte OIDC explicitamente ativada."""

    settings = OAuthTokenVerifierSettings.from_prefixed_environ(os.environ)
    return OAuthAccessTokenVerifier(settings)


def _oauth_resource_metadata_url(surface: McpSurface | str) -> str:
    base_url = _coerce_str(os.environ.get("APP32_MCP_PUBLIC_BASE_URL")) or "https://app.gestaoversus.com.br"
    return (
        f"{base_url.rstrip('/')}/.well-known/oauth-protected-resource/"
        f"mcp/{normalize_surface(surface)}"
    )


def _oauth_www_authenticate(
    *,
    surface: McpSurface | str,
    error: str,
    detail: str,
) -> str:
    # O valor é construído exclusivamente da configuração do servidor; nem
    # token nem header do cliente participam da URL do resource metadata.
    # Headers HTTP devem ser ASCII. O detalhe completo (UTF-8) fica apenas no
    # corpo JSON; isso evita erro de codificação no adaptador ASGI.
    header_detail = detail.encode("ascii", "ignore").decode("ascii").replace('"', "'")
    return (
        f'Bearer error="{error}", error_description="{header_detail}", '
        f'resource_metadata="{_oauth_resource_metadata_url(surface)}"'
    )


def _resolve_oauth_identity(
    *,
    token: str,
    surface: McpSurface | str,
) -> OAuthHttpIdentityResolution:
    """Resolve OIDC sem fallback ao registry interno ou a token DB-backed."""

    normalized_surface = normalize_surface(surface)
    if not _principal_grant_gate_enabled():
        # Um principal OIDC sem o gate de grant poderia alcançar o caminho
        # legado de ``resolve_runtime_identity``. Falhar antes do callback é
        # preferível a habilitar OAuth parcialmente.
        return OAuthHttpIdentityResolution(
            identity=None,
            status_code=503,
            error="oauth_configuration_error",
            detail="OAuth requer APP32_MCP_USE_PRINCIPAL_GRANTS ativo para a coorte.",
        )

    try:
        verified = load_oauth_access_token_verifier().verify(token)
    except (OAuthTokenVerificationError, ValueError):
        return OAuthHttpIdentityResolution(
            identity=None,
            status_code=401,
            error="invalid_token",
            detail="Access token OAuth inválido, expirado ou incompatível com este resource server.",
        )

    required_surface_scope = f"mcp:{normalized_surface}"
    if required_surface_scope not in set(verified.scopes):
        return OAuthHttpIdentityResolution(
            identity=None,
            status_code=403,
            error="insufficient_scope",
            detail=f"Scope obrigatório para a surface: {required_surface_scope}",
        )

    from services.principal_authorization_service import principal_authorization_service

    try:
        external_resolution = principal_authorization_service.resolve_external_principal(
            issuer=verified.issuer,
            subject=verified.subject,
        )
    except Exception:
        # Indisponibilidade do banco/vínculo não pode converter um JWT válido
        # em autorização implícita nem revelar detalhes internos ao conector.
        return OAuthHttpIdentityResolution(
            identity=None,
            status_code=503,
            error="oauth_identity_unavailable",
            detail="Resolução de identidade OAuth indisponível temporariamente.",
        )
    principal = external_resolution.principal if external_resolution.allowed else None
    if principal is None or principal.id is None:
        return OAuthHttpIdentityResolution(
            identity=None,
            status_code=401,
            error="invalid_token",
            detail="Identidade OAuth não possui vínculo ativo no APP32.",
        )

    return OAuthHttpIdentityResolution(
        identity=App32McpHttpIdentity(
            # O JWT não é exposto fora da fronteira HTTP; o campo permanece
            # apenas para compatibilidade com o contrato do SDK MCP.
            token=token,
            user_id=_coerce_optional_int(getattr(principal, "user_id", None)),
            company_id=None,
            principal_id=principal.id,
            subject_type=_coerce_str(getattr(principal, "subject_type", None)) or "USER",
            issuer=verified.issuer,
            subject=verified.subject,
            auth_method="oauth_oidc_bearer",
            fallback_role="colaborador",
            allowed_surfaces=(normalized_surface,),
            scopes=verified.scopes,
            client_id=verified.client_id or "oauth-client",
            metadata={
                "oauth_expires_at": verified.expires_at,
                "mcp_enabled": True,
                "training_completed": True,
            },
        ),
        status_code=200,
    )


def _resolve_db_backed_identity(
    request: Request | None,
    *,
    token: str,
    surface: McpSurface | str,
) -> App32McpHttpIdentity | None:
    company_id = None
    client_name = None
    if request is not None:
        company_id = _coerce_optional_int(
            _coerce_str(request.headers.get(HTTP_CONTEXT_HEADER_MAP["company_id"]) or request.query_params.get("company_id"))
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
        principal_id=None,
        subject_type="USER",
        issuer=None,
        subject=resolved.subject,
        auth_method="internal_bearer",
        # Papel é uma decisão do APP32, derivada do vínculo persistido do
        # principal com o tenant. Header/query nunca pode elevá-lo no fluxo
        # DB-backed; o request só pode solicitar contexto que o service irá
        # validar (por exemplo, company_id).
        fallback_role=resolved.fallback_role,
        allowed_surfaces=resolved.allowed_surfaces,
        scopes=("mcp:access",),
        client_id="app32-mcp-user-token",
        metadata={
            "subject": resolved.subject,
            "client_name": resolved.client_name,
            "user_mcp_token_id": resolved.token_record_id,
            "runtime_profile": getattr(resolved, "runtime_profile", None),
            "actor_type": getattr(resolved, "actor_type", None),
            "harness_key": getattr(resolved, "harness_key", None),
            "harness_label": getattr(resolved, "harness_label", None),
            "company_resolution_source": getattr(resolved, "company_resolution_source", None),
            "accessible_company_ids": list(getattr(resolved, "accessible_company_ids", ()) or ()),
            "multi_company": bool(getattr(resolved, "multi_company", False)),
            "mcp_enabled": getattr(resolved, "mcp_enabled", True),
            "training_completed": getattr(resolved, "training_completed", True),
        },
    )


class App32MCPTokenVerifier(TokenVerifier):
    def __init__(self, *, surface: McpSurface | str, oauth_enabled: bool | None = None):
        self.surface = normalize_surface(surface)
        self.oauth_enabled = oauth_enabled

    async def verify_token(self, token: str) -> AccessToken | None:
        if oauth_transport_enabled_for_surface(self.surface, forced=self.oauth_enabled):
            resolution = _resolve_oauth_identity(token=token, surface=self.surface)
            identity = resolution.identity
        else:
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
            expires_at=_coerce_optional_int(identity.metadata.get("oauth_expires_at")),
            subject=identity.subject,
            claims={"iss": identity.issuer} if identity.issuer else None,
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


def resolve_request_identity(request: Request, *, surface: McpSurface | str, oauth_enabled: bool | None = None) -> App32McpHttpIdentity | None:
    token = extract_bearer_token(request)
    if not token:
        return None
    if oauth_transport_enabled_for_surface(surface):
        # Coorte OAuth é exclusiva por surface. Um JWT rejeitado, uma
        # identidade não vinculada ou um scope insuficiente nunca passa para
        # APP32_MCP_HTTP_TOKEN nem para user_mcp_tokens.
        return _resolve_oauth_identity(token=token, surface=surface).identity
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
        principal_id=identity.principal_id,
        subject_type=identity.subject_type,
        issuer=identity.issuer,
        subject=identity.subject,
        auth_method=identity.auth_method,
        fallback_role=fallback_role or identity.fallback_role,
        allowed_surfaces=identity.allowed_surfaces,
        scopes=identity.scopes,
        client_id=identity.client_id,
        metadata=dict(identity.metadata),
    )


def _build_identity_context_payload(
    identity: App32McpHttpIdentity,
    *,
    surface: McpSurface | str,
    thread_id: str | None = None,
    runtime_profile: str | None = None,
    actor_type: str | None = None,
) -> dict[str, Any]:
    normalized_runtime_profile = normalize_runtime_profile(
        runtime_profile or _coerce_str(identity.metadata.get("runtime_profile"))
    )
    runtime_spec = get_runtime_profile_spec(normalized_runtime_profile)
    resolved_actor_type = (
        actor_type
        or _coerce_str(identity.metadata.get("actor_type"))
        or (runtime_spec.actor_type if runtime_spec else None)
    )
    harness_key = _coerce_str(identity.metadata.get("harness_key")) or (
        runtime_spec.default_harness_key if runtime_spec else None
    )
    harness_label = _coerce_str(identity.metadata.get("harness_label")) or (
        runtime_spec.default_harness_label if runtime_spec else None
    )
    return {
        "user_id": identity.user_id,
        "principal_id": identity.principal_id,
        "subject_type": identity.subject_type,
        "issuer": identity.issuer,
        "subject": identity.subject,
        "auth_method": identity.auth_method,
        "token_scopes": list(identity.scopes),
        "company_id": identity.company_id,
        "fallback_role": identity.fallback_role,
        "surface": normalize_surface(surface),
        "transport": "streamable_http",
        "client": "claude_remote_connector",
        "thread_id": thread_id,
        "runtime_profile": normalized_runtime_profile,
        "actor_type": resolved_actor_type,
        "runtime_family": runtime_spec.family_key if runtime_spec else normalized_runtime_profile,
        "runtime_family_label": runtime_spec.family_label if runtime_spec else normalized_runtime_profile,
        "harness_key": harness_key,
        "harness_label": harness_label,
        "client_id": identity.client_id,
        "correlation_id": _coerce_str(identity.metadata.get("correlation_id")),
        "company_resolution_source": _coerce_str(identity.metadata.get("company_resolution_source")),
        "accessible_company_ids": list(identity.metadata.get("accessible_company_ids") or []),
        "multi_company": bool(identity.metadata.get("multi_company", False)),
        "selection_required_for_mutations": bool(
            identity.metadata.get("multi_company", False) and identity.company_id is None
        ),
        "disable_company_fallback": bool(identity.metadata.get("multi_company", False)),
        "mcp_enabled": bool(identity.metadata.get("mcp_enabled", True)),
        "training_completed": bool(identity.metadata.get("training_completed", True)),
    }


def resolve_request_context_payload(request: Request, *, surface: McpSurface | str, oauth_enabled: bool | None = None) -> dict[str, Any]:
    identity = resolve_request_identity(request, surface=surface, oauth_enabled=oauth_enabled)
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
    return _build_identity_context_payload(
        identity,
        surface=surface,
        thread_id=thread_id,
        runtime_profile=runtime_profile,
        actor_type=actor_type,
    )


class App32MCPRequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, surface: McpSurface | str, oauth_enabled: bool | None = None):
        super().__init__(app)
        self.surface = normalize_surface(surface)
        self.oauth_enabled = oauth_enabled

    async def dispatch(self, request: Request, call_next):
        oauth_resolution: OAuthHttpIdentityResolution | None = None
        if oauth_transport_enabled_for_surface(self.surface, forced=self.oauth_enabled):
            token = extract_bearer_token(request)
            oauth_resolution = (
                _resolve_oauth_identity(token=token, surface=self.surface)
                if token
                else OAuthHttpIdentityResolution(
                    identity=None,
                    status_code=401,
                    error="invalid_token",
                    detail="Access token OAuth ausente.",
                )
            )
            identity = oauth_resolution.identity
        else:
            identity = resolve_request_identity(request, surface=self.surface, oauth_enabled=self.oauth_enabled)
        if identity is None:
            if oauth_resolution is not None:
                error = oauth_resolution.error or "invalid_token"
                detail = oauth_resolution.detail or "Access token OAuth rejeitado."
                return JSONResponse(
                    {"error": error, "detail": detail},
                    status_code=oauth_resolution.status_code,
                    headers={
                        "WWW-Authenticate": _oauth_www_authenticate(
                            surface=self.surface,
                            error=error,
                            detail=detail,
                        )
                    },
                )
            return JSONResponse({"error": "unauthorized", "detail": "Bearer token inválido ou ausente."}, status_code=401)

        accept_header = request.headers.get("accept", "")
        mcp_session_id = request.headers.get("mcp-session-id")
        if (
            request.method.upper() == "GET"
            and "text/event-stream" in accept_header.lower()
            and not mcp_session_id
        ):
            return JSONResponse(
                {
                    "error": "sse_transport_not_supported",
                    "detail": (
                        "O MCP remoto do APP32 usa streamable-http. "
                        "Configure o cliente para transporte streamable-http em vez de SSE."
                    ),
                    "transport": "streamable-http",
                    "sse_supported": False,
                },
                status_code=400,
            )

        if (
            (identity.user_id is None and identity.principal_id is None)
            # OAuth nunca fixa tenant no token/contexto HTTP. Para qualquer
            # surface da coorte, permitir apenas o handshake/descoberta sem
            # empresa e deixar cada tool exigir company_id via grant. Tokens
            # legados continuam precisando de company_id fora de ``user``.
            or (
                identity.company_id is None
                and self.surface != "user"
                and identity.principal_id is None
            )
        ):
            return JSONResponse(
                {
                    "error": "invalid_context",
                    "detail": "Token MCP sem user_id/company_id associado. Configure APP32_MCP_HTTP_TOKENS_JSON ou APP32_MCP_HTTP_TOKEN.",
                },
                status_code=403,
            )

        payload = resolve_request_context_payload(request, surface=self.surface, oauth_enabled=self.oauth_enabled)
        channel_gate = evaluate_mcp_channel_gate(
            McpChannelGateRequest(
                surface=self.surface,
                runtime_profile=_coerce_str(payload.get("runtime_profile")),
                actor_type=_coerce_str(payload.get("actor_type")),
                mcp_enabled=bool(payload.get("mcp_enabled", True)),
                training_completed=bool(payload.get("training_completed", True)),
            )
        )
        if not channel_gate.allowed:
            return JSONResponse(
                {
                    "error": "mcp_channel_denied",
                    "detail": channel_gate.reason,
                    "checks": list(channel_gate.checks),
                },
                status_code=403,
            )
        request.scope["app32_mcp_context"] = dict(payload)
        tokens = set_http_request_context(identity, payload)
        try:
            try:
                return await call_next(request)
            except RuntimeError as exc:
                if "No response returned" not in str(exc):
                    raise
                return JSONResponse(
                    {
                        "error": "mcp_runtime_temporarily_unavailable",
                        "detail": "O runtime MCP está reiniciando. Reabra a sessão streamable-http e repita apenas a leitura idempotente.",
                        "retryable": True,
                        "retry_after_seconds": 2,
                    },
                    status_code=503,
                    headers={"Retry-After": "2"},
                )
        finally:
            reset_http_request_context(tokens)


def build_oauth_preparation(base_url: str | None = None) -> App32OAuthPreparation:
    # APP32_MCP_OAUTH_* é o placeholder histórico. Quando há uma coorte OIDC
    # real, o issuer exposto pelo resource metadata é obrigatoriamente o IdP
    # externo previamente configurado, nunca um authorization server APP32.
    issuer_url = _coerce_str(os.environ.get("APP32_MCP_OIDC_ISSUER")) or _coerce_str(
        os.environ.get("APP32_MCP_OAUTH_ISSUER_URL")
    )
    resource_server_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_RESOURCE_SERVER_URL"))
    service_documentation_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_DOCS_URL"))

    normalized_base = _coerce_str(base_url or os.environ.get("APP32_MCP_PUBLIC_BASE_URL"))
    if issuer_url is None and normalized_base:
        issuer_url = normalized_base.rstrip("/") + "/oauth"
    if resource_server_url is None and normalized_base:
        resource_server_url = normalized_base.rstrip("/")

    enabled = bool(
        _env_flag("APP32_MCP_HTTP_ENABLE_OAUTH", default=False)
        and _oauth_enabled_surfaces()
        and issuer_url
        and resource_server_url
    )
    return App32OAuthPreparation(
        enabled=enabled,
        issuer_url=issuer_url,
        service_documentation_url=service_documentation_url,
        resource_server_url=resource_server_url,
    )


def build_auth_settings(
    base_url: str | None = None,
    *,
    surface: McpSurface | str | None = None,
    oauth_enabled: bool | None = None,
) -> AuthSettings | None:
    if surface is not None and oauth_transport_enabled_for_surface(surface, forced=oauth_enabled):
        if not _principal_grant_gate_enabled():
            raise ValueError(
                "OAuth MCP requer APP32_MCP_USE_PRINCIPAL_GRANTS=1 para a coorte configurada."
            )
        oidc_settings = load_oauth_access_token_verifier().settings
        resource_server_url = _coerce_str(base_url or os.environ.get("APP32_MCP_PUBLIC_BASE_URL"))
        if not resource_server_url:
            raise ValueError("APP32_MCP_PUBLIC_BASE_URL é obrigatório para OAuth MCP.")
        return AuthSettings(
            issuer_url=oidc_settings.issuer,
            service_documentation_url=_coerce_str(os.environ.get("APP32_MCP_OAUTH_DOCS_URL")),
            required_scopes=["mcp:access"],
            resource_server_url=resource_server_url,
        )

    normalized_base = _coerce_str(base_url or os.environ.get("APP32_MCP_PUBLIC_BASE_URL"))
    # Surfaces fora da coorte OIDC mantêm exatamente o contrato legado. Elas
    # não podem anunciar o issuer externo enquanto ainda aceitam token interno.
    legacy_issuer_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_ISSUER_URL"))
    legacy_resource_server_url = _coerce_str(os.environ.get("APP32_MCP_OAUTH_RESOURCE_SERVER_URL"))
    issuer_url = legacy_issuer_url or normalized_base
    resource_server_url = legacy_resource_server_url or normalized_base
    if not issuer_url or not resource_server_url:
        return None
    return AuthSettings(
        issuer_url=issuer_url,
        service_documentation_url=_coerce_str(os.environ.get("APP32_MCP_OAUTH_DOCS_URL")),
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
