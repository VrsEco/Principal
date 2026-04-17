from __future__ import annotations

import os
import sys
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

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
    build_user_mcp_server,
)

try:  # pragma: no cover - dependência opcional em ambiente de teste
    import uvicorn
except ImportError:  # pragma: no cover
    uvicorn = None


DEFAULT_HOST = os.environ.get("APP32_MCP_HTTP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("APP32_MCP_HTTP_PORT", "8101"))
DEFAULT_PUBLIC_BASE_URL = os.environ.get("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")


def _surface_mount_path(surface: str) -> str:
    return f"/mcp/{surface}"


def _make_exact_surface_entrypoint(surface_app, mount_path: str):
    class _ExactSurfaceEntrypoint:
        async def __call__(self, scope, receive, send):
            rewritten_scope = dict(scope)
            rewritten_scope["root_path"] = f"{scope.get('root_path', '')}{mount_path}"
            rewritten_scope["path"] = "/"
            await surface_app(rewritten_scope, receive, send)

    return _ExactSurfaceEntrypoint()


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
    else:  # pragma: no cover - proteção defensiva
        raise ValueError(f"Surface HTTP MCP inválida: {surface!r}")

    mcp.settings.host = DEFAULT_HOST
    mcp.settings.port = DEFAULT_PORT
    mcp.settings.streamable_http_path = "/"
    mcp.settings.mount_path = "/"
    mcp.settings.stateless_http = False
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
            },
            "auth_mode": {
                "mvp_token_registry_loaded": len(load_http_token_registry()),
                "oauth_ready_flag": oauth_preparation.enabled,
                "issuer_url": oauth_preparation.issuer_url,
                "resource_server_url": oauth_preparation.resource_server_url,
            },
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

    routes = [
        Route("/", endpoint=_index),
        Route("/healthz", endpoint=_healthz),
        Route(_surface_mount_path("user"), endpoint=_make_exact_surface_entrypoint(user_app, _surface_mount_path("user"))),
        Route(_surface_mount_path("admin"), endpoint=_make_exact_surface_entrypoint(admin_app, _surface_mount_path("admin"))),
        Route(
            _surface_mount_path("analytics"),
            endpoint=_make_exact_surface_entrypoint(analytics_app, _surface_mount_path("analytics")),
        ),
        Mount(_surface_mount_path("user"), app=user_app),
        Mount(_surface_mount_path("admin"), app=admin_app),
        Mount(_surface_mount_path("analytics"), app=analytics_app),
    ]
    return Starlette(debug=False, routes=routes)


def run_mcp_http_server() -> None:
    if uvicorn is None:  # pragma: no cover
        raise RuntimeError("uvicorn não encontrado. Instale a dependência antes de subir o MCP HTTP.")

    app = create_http_app()
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, log_level=os.environ.get("APP32_MCP_HTTP_LOG_LEVEL", "info"))


if __name__ == "__main__":  # pragma: no cover - entrypoint manual
    run_mcp_http_server()
