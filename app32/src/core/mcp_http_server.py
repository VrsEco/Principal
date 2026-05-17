from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
import os
import sys
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route


def _normalize_import_path() -> str:
    package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    shadow_path = os.path.abspath(os.path.dirname(__file__))

    normalized_sys_path: list[str] = []
    for entry in sys.path:
        resolved = os.path.abspath(entry or os.getcwd())
        if resolved == shadow_path:
            continue
        if resolved == package_root:
            continue
        normalized_sys_path.append(entry)

    sys.path[:] = [package_root, *normalized_sys_path]
    return package_root


_normalize_import_path()

from src.core.mcp_http_auth import (  # noqa: E402
    App32MCPRequestContextMiddleware,
    App32MCPTokenVerifier,
    build_auth_settings,
    build_oauth_preparation,
    load_http_token_registry,
)
from src.core.mcp_surface_registry import (  # noqa: E402
    build_admin_mcp_server,
    build_analytics_mcp_server,
    build_ops_mcp_server,
    build_user_mcp_server,
)

try:  # pragma: no cover - dependência opcional em ambiente de teste
    import uvicorn
except ImportError:  # pragma: no cover
    uvicorn = None


DEFAULT_HOST = os.environ.get("APP32_MCP_HTTP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("APP32_MCP_HTTP_PORT", "8101"))
DEFAULT_PUBLIC_BASE_URL = os.environ.get("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")


def _env_flag(name: str, default: bool) -> bool:
    raw = str(os.environ.get(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


DEFAULT_STATELESS_HTTP = _env_flag("APP32_MCP_HTTP_STATELESS", True)


def _surface_mount_path(surface: str) -> str:
    return f"/mcp/{surface}"


def build_surface_http_app(surface: str):
    """
    Constrói uma app Starlette montável em `/mcp/<surface>`.

    Reaproveita a montagem canônica de tools do surface registry, sem tocar no
    runtime stdio existente.
    """
    if surface == "user":
        mcp = build_user_mcp_server(name="GestaoVersus User Remote MCP")
    elif surface == "admin":
        mcp = build_admin_mcp_server(name="GestaoVersus Admin Remote MCP")
    elif surface == "analytics":
        mcp = build_analytics_mcp_server(name="GestaoVersus Analytics Remote MCP")
    elif surface == "ops":
        mcp = build_ops_mcp_server(name="GestaoVersus Ops Remote MCP")
    else:  # pragma: no cover - proteção defensiva
        raise ValueError(f"Surface HTTP MCP inválida: {surface!r}")

    mcp.settings.host = DEFAULT_HOST
    mcp.settings.port = DEFAULT_PORT
    mcp.settings.streamable_http_path = "/"
    mcp.settings.mount_path = "/"
    mcp.settings.stateless_http = DEFAULT_STATELESS_HTTP
    mcp.settings.auth = build_auth_settings(
        base_url=f"{DEFAULT_PUBLIC_BASE_URL.rstrip('/')}{_surface_mount_path(surface)}"
    )
    mcp._token_verifier = App32MCPTokenVerifier(surface=surface)  # noqa: SLF001

    app = mcp.streamable_http_app()
    app.add_middleware(App32MCPRequestContextMiddleware, surface=surface)
    return app


async def _healthz(_: Request) -> JSONResponse:
    oauth_preparation = build_oauth_preparation(base_url=DEFAULT_PUBLIC_BASE_URL)
    return JSONResponse(
        {
            "ok": True,
            "transport": "streamable-http",
            "public_base_url": DEFAULT_PUBLIC_BASE_URL.rstrip("/"),
            "surfaces": {
                "user": _surface_mount_path("user"),
                "admin": _surface_mount_path("admin"),
                "analytics": _surface_mount_path("analytics"),
                "ops": _surface_mount_path("ops"),
            },
            "auth_mode": {
                "mvp_token_registry_loaded": len(load_http_token_registry()),
                "oauth_ready_flag": oauth_preparation.enabled,
                "issuer_url": oauth_preparation.issuer_url,
                "resource_server_url": oauth_preparation.resource_server_url,
            },
            "stateless_http": DEFAULT_STATELESS_HTTP,
        }
    )


async def _index(_: Request) -> JSONResponse:
    base = DEFAULT_PUBLIC_BASE_URL.rstrip("/")
    return JSONResponse(
        {
            "service": "app32-mcp-http",
            "description": "MCP remoto do APP32 para uso via HTTPS/claude.ai.",
            "streamable_http_endpoints": {
                "user": f"{base}{_surface_mount_path('user')}",
                "admin": f"{base}{_surface_mount_path('admin')}",
                "analytics": f"{base}{_surface_mount_path('analytics')}",
                "ops": f"{base}{_surface_mount_path('ops')}",
            },
            "requirements": {
                "authorization": "Bearer token (MVP interno) / OAuth (preparação de arquitetura).",
                "tenant_isolation": "company_id resolvido por token/contexto autenticado.",
            },
        }
    )


def create_http_app() -> Starlette:
    user_app = build_surface_http_app("user")
    admin_app = build_surface_http_app("admin")
    analytics_app = build_surface_http_app("analytics")
    ops_app = build_surface_http_app("ops")

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with AsyncExitStack() as stack:
            for surface_app in (user_app, admin_app, analytics_app, ops_app):
                await stack.enter_async_context(surface_app.router.lifespan_context(surface_app))
            yield

    routes = [
        Route("/", endpoint=_index),
        Route("/healthz", endpoint=_healthz),
        Mount(_surface_mount_path("user"), app=user_app),
        Mount(_surface_mount_path("admin"), app=admin_app),
        Mount(_surface_mount_path("analytics"), app=analytics_app),
        Mount(_surface_mount_path("ops"), app=ops_app),
    ]
    return Starlette(debug=False, routes=routes, lifespan=lifespan)


def run_mcp_http_server() -> None:
    if uvicorn is None:  # pragma: no cover
        raise RuntimeError("uvicorn não encontrado. Instale a dependência antes de subir o MCP HTTP.")

    app = create_http_app()
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, log_level=os.environ.get("APP32_MCP_HTTP_LOG_LEVEL", "info"))


if __name__ == "__main__":  # pragma: no cover - entrypoint manual
    run_mcp_http_server()
