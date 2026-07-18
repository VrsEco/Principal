from __future__ import annotations

import sys
from typing import Any, Literal, Sequence

from src.intelligence.tool_catalog import catalog
from src.intelligence.tooling.capabilities import ToolScope, build_capability_manifest, infer_tool_action
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.core.mcp_runtime import resolve_mcp_execution_context, wrap_mcp_callable

try:  # pragma: no cover - dependência opcional em ambiente de teste
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - fallback quando o pacote não está instalado
    FastMCP = None

McpSurface = Literal["user", "admin", "analytics", "ops"]

_SURFACE_SCOPE_FILTERS: dict[McpSurface, tuple[str, ...]] = {
    "user": (ToolScope.MCP_USER.value,),
    "analytics": (ToolScope.MCP_ANALYTICS.value,),
    "ops": (ToolScope.MCP_OPS.value,),
    "admin": (ToolScope.MCP_ADMIN.value,),
}


def normalize_surface(surface: McpSurface | str) -> McpSurface:
    normalized = str(surface).strip().lower()
    if normalized not in _SURFACE_SCOPE_FILTERS:
        raise ValueError(f"Surface MCP inválida: {surface!r}")
    return normalized  # type: ignore[return-value]


def get_surface_scope_filter(surface: McpSurface | str) -> tuple[str, ...]:
    normalized = normalize_surface(surface)
    return _SURFACE_SCOPE_FILTERS[normalized]


def get_surface_manifest(
    surface: McpSurface | str,
    *,
    domain: str | Sequence[str] | None = None,
    include_tools: bool = True,
) -> dict[str, Any]:
    normalized_surface = normalize_surface(surface)
    capabilities = list(
        catalog.iter_capabilities(
            scope=get_surface_scope_filter(normalized_surface),
            domain=domain,
        )
    )
    try:
        execution_context = resolve_mcp_execution_context({})
    except RuntimeError:
        execution_context = None

    if execution_context is not None and execution_context.user_id is not None:
        filtered_capabilities = []
        for capability in capabilities:
            decision = evaluate_tool_policy(
                {
                    "user_id": execution_context.user_id,
                    "company_id": execution_context.company_id,
                    "employee_id": execution_context.employee_id,
                    "role": execution_context.role,
                    "channel": execution_context.channel,
                    "thread_id": execution_context.thread_id,
                    "permissions": execution_context.permissions,
                    "metadata": dict(execution_context.metadata or {}),
                },
                    ToolPolicyRequest(
                        tool_name=capability.name,
                        surface=normalized_surface,
                        domain=capability.domain,
                        action=infer_tool_action(capability.name, capability.domain),
                        risk=getattr(capability.risk, "value", capability.risk),
                        requested_company_id=execution_context.company_id,
                        accessible_company_ids=execution_context.accessible_company_ids,
                        required_permissions=capability.permissions,
                        confirmed_mutation=not capability.human_gate,
                        required_context=tuple(getattr(capability, "required_context", ()) or ()),
                        metadata=dict(execution_context.metadata or {}),
                    ),
                )
            if decision.allowed:
                filtered_capabilities.append(capability)
        capabilities = filtered_capabilities

    return build_capability_manifest(
        capabilities,
        scope=None,
        domain=None,
        include_tools=include_tools,
    )


def iter_surface_tool_names(surface: McpSurface | str) -> list[str]:
    manifest = get_surface_manifest(surface, include_tools=True)
    return [tool["name"] for tool in manifest.get("tools", [])]


def _get_surface_manifest_in_app_context(
    surface: McpSurface | str,
    *,
    domain: str | Sequence[str] | None = None,
    include_tools: bool = True,
) -> dict[str, Any]:
    """Avalia manifesto e policy com o mesmo contexto Flask/tenant do runtime."""
    from flask import has_app_context

    if has_app_context():
        return get_surface_manifest(surface, domain=domain, include_tools=include_tools)

    from app import create_app

    app = create_app()
    with app.app_context():
        return get_surface_manifest(surface, domain=domain, include_tools=include_tools)


def _build_policy_fast_mcp(name: str, surface: McpSurface | str) -> Any:
    """Cria servidor cujo tools/list reflete a policy efetiva da requisição."""
    if FastMCP is None:  # pragma: no cover
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    normalized_surface = normalize_surface(surface)
    if not hasattr(FastMCP, "list_tools"):
        return FastMCP(name)

    class _PolicyFastMCP(FastMCP):
        async def list_tools(self):
            tools = await super().list_tools()
            manifest = _get_surface_manifest_in_app_context(
                normalized_surface,
                include_tools=True,
            )
            allowed_names = {tool["name"] for tool in manifest.get("tools", [])}
            allowed_names.add(f"list_{normalized_surface}_app32_capabilities")
            return [tool for tool in tools if tool.name in allowed_names]

    return _PolicyFastMCP(name)


def _tool_map() -> dict[str, Any]:
    return {getattr(tool, "name", str(tool)): tool for tool in catalog.get_langchain_tools()}


def _register_tool(mcp: Any, tool: Any) -> None:
    if hasattr(tool, "func"):
        mcp.tool(name=tool.name, description=tool.description)(wrap_mcp_callable(tool.func))
        return

    def make_wrapper(current_tool: Any):
        @mcp.tool(name=current_tool.name, description=current_tool.description)
        @wrap_mcp_callable
        def mcp_tool_wrapper(*args, **kwargs):
            payload = kwargs if kwargs else args[0] if args else {}
            return current_tool.invoke(payload)

        return mcp_tool_wrapper

    make_wrapper(tool)


def _register_shared_registrars(mcp: Any) -> None:
    class _WrappedMCPProxy:
        def __init__(self, target: Any):
            self._target = target

        def tool(self, *args, **kwargs):
            decorator = self._target.tool(*args, **kwargs)
            explicit_name = kwargs.get("name")

            def _decorate(func):
                tool_name = explicit_name or getattr(func, "__name__", "unknown_tool")
                wrapped = wrap_mcp_callable(func)
                setattr(wrapped, "__app32_tool_name__", tool_name)
                return decorator(wrapped)

            if args and callable(args[0]) and not kwargs:
                return _decorate(args[0])
            return _decorate

        def __getattr__(self, item):
            return getattr(self._target, item)

    proxy = _WrappedMCPProxy(mcp)
    for registrar in getattr(catalog, "mcp_registrars", ()):
        registrar(proxy)


def _register_admin_diagnostics(mcp: Any) -> None:
    @mcp.tool(
        name="get_system_health",
        description="Verifica a saúde do banco de dados e do servidor.",
    )
    def get_system_health() -> str:
        from src.core.database import db

        status, msg = db.health_check()
        return f"Database: {'OK' if status else 'ERROR'} - {msg}"

    @mcp.tool(
        name="get_database_schema",
        description="Retorna uma visão geral das tabelas do banco de dados.",
    )
    def get_database_schema() -> str:
        from sqlalchemy import text

        from src.core.database import db

        try:
            with db.engine.connect() as connection:
                query = text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
                result = connection.execute(query)
                tables = [row[0] for row in result]
                return f"Tabelas ativas: {', '.join(tables)}"
        except Exception as exc:  # pragma: no cover - proteção defensiva
            return f"Erro ao ler schema: {exc}"


def register_mcp_surface_tools(
    mcp: Any,
    surface: McpSurface | str,
    *,
    include_shared_registrars: bool = True,
    include_admin_diagnostics: bool = False,
) -> None:
    normalized_surface = normalize_surface(surface)
    allowed_names = set(iter_surface_tool_names(normalized_surface))
    tools_by_name = _tool_map()

    for tool_name in sorted(allowed_names):
        tool = tools_by_name.get(tool_name)
        if tool is None:
            continue
        _register_tool(mcp, tool)

    if include_shared_registrars:
        _register_shared_registrars(mcp)

    @mcp.tool(
        name=f"list_{normalized_surface}_app32_capabilities",
        description=(
            "Lista as capacidades e metadados de segurança do catálogo MCP/Sapiens "
            f"do APP32 para a superfície {normalized_surface}."
        ),
    )
    def list_surface_capabilities(
        domain: str | None = None,
        include_tools: bool = True,
    ) -> dict[str, Any]:
        """Manifesto consultável por agentes para descoberta de capacidades."""

        manifest_loader = (
            _get_surface_manifest_in_app_context
            if normalized_surface == "user"
            else get_surface_manifest
        )
        return manifest_loader(
            normalized_surface,
            domain=domain,
            include_tools=include_tools,
        )

    if normalized_surface == "admin" and include_admin_diagnostics:
        _register_admin_diagnostics(mcp)


def register_user_mcp_tools(
    mcp: Any,
    *,
    include_shared_registrars: bool = True,
) -> None:
    register_mcp_surface_tools(
        mcp,
        "user",
        include_shared_registrars=include_shared_registrars,
        include_admin_diagnostics=False,
    )


def register_admin_mcp_tools(
    mcp: Any,
    *,
    include_shared_registrars: bool = True,
    include_admin_diagnostics: bool = True,
) -> None:
    register_mcp_surface_tools(
        mcp,
        "admin",
        include_shared_registrars=include_shared_registrars,
        include_admin_diagnostics=include_admin_diagnostics,
    )


def register_analytics_mcp_tools(
    mcp: Any,
    *,
    include_shared_registrars: bool = True,
) -> None:
    register_mcp_surface_tools(
        mcp,
        "analytics",
        include_shared_registrars=include_shared_registrars,
        include_admin_diagnostics=False,
    )


def register_ops_mcp_tools(
    mcp: Any,
    *,
    include_shared_registrars: bool = True,
) -> None:
    register_mcp_surface_tools(
        mcp,
        "ops",
        include_shared_registrars=include_shared_registrars,
        include_admin_diagnostics=False,
    )


def build_user_mcp_server(name: str = "GestaoVersus User MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = _build_policy_fast_mcp(name, "user")
    register_user_mcp_tools(mcp)
    return mcp


def build_admin_mcp_server(name: str = "GestaoVersus Admin MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = _build_policy_fast_mcp(name, "admin")
    register_admin_mcp_tools(mcp)
    return mcp


def build_analytics_mcp_server(name: str = "GestaoVersus Analytics MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = _build_policy_fast_mcp(name, "analytics")
    register_analytics_mcp_tools(mcp)
    return mcp


def build_ops_mcp_server(name: str = "GestaoVersus Ops MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = _build_policy_fast_mcp(name, "ops")
    register_ops_mcp_tools(mcp)
    return mcp


def run_user_mcp_server() -> None:
    mcp = build_user_mcp_server()
    print("Iniciando MCP User Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()


def run_analytics_mcp_server() -> None:
    mcp = build_analytics_mcp_server()
    print("Iniciando MCP Analytics Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()


def run_ops_mcp_server() -> None:
    mcp = build_ops_mcp_server()
    print("Iniciando MCP Ops Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()


def run_admin_mcp_server() -> None:
    mcp = build_admin_mcp_server()
    print("Iniciando MCP Admin Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()
