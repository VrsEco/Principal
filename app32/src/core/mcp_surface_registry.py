from __future__ import annotations

from typing import Any, Literal, Sequence

from src.intelligence.tool_catalog import catalog
from src.intelligence.tooling.capabilities import ToolScope

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
    return catalog.get_capability_manifest(
        scope=get_surface_scope_filter(surface),
        domain=domain,
        include_tools=include_tools,
    )


def iter_surface_tool_names(surface: McpSurface | str) -> list[str]:
    manifest = get_surface_manifest(surface, include_tools=True)
    return [tool["name"] for tool in manifest.get("tools", [])]


def _tool_map() -> dict[str, Any]:
    return {getattr(tool, "name", str(tool)): tool for tool in catalog.get_langchain_tools()}


def _register_tool(mcp: Any, tool: Any) -> None:
    if hasattr(tool, "func"):
        mcp.tool(name=tool.name, description=tool.description)(tool.func)
        return

    def make_wrapper(current_tool: Any):
        @mcp.tool(name=current_tool.name, description=current_tool.description)
        def mcp_tool_wrapper(*args, **kwargs):
            payload = kwargs if kwargs else args[0] if args else {}
            return current_tool.invoke(payload)

        return mcp_tool_wrapper

    make_wrapper(tool)


def _register_shared_registrars(mcp: Any) -> None:
    for registrar in getattr(catalog, "mcp_registrars", ()):
        registrar(mcp)


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

        return get_surface_manifest(
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
    mcp = FastMCP(name)
    register_user_mcp_tools(mcp)
    return mcp


def build_admin_mcp_server(name: str = "GestaoVersus Admin MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = FastMCP(name)
    register_admin_mcp_tools(mcp)
    return mcp


def build_analytics_mcp_server(name: str = "GestaoVersus Analytics MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = FastMCP(name)
    register_analytics_mcp_tools(mcp)
    return mcp


def build_ops_mcp_server(name: str = "GestaoVersus Ops MCP") -> Any:
    if FastMCP is None:  # pragma: no cover - ambiente sem dependência MCP
        raise RuntimeError("Biblioteca 'mcp' não encontrada.")
    mcp = FastMCP(name)
    register_ops_mcp_tools(mcp)
    return mcp


def run_user_mcp_server() -> None:
    mcp = build_user_mcp_server()
    print("Iniciando MCP User Server via STDIO (AI-Readable Mode)...")
    mcp.run()


def run_analytics_mcp_server() -> None:
    mcp = build_analytics_mcp_server()
    print("Iniciando MCP Analytics Server via STDIO (AI-Readable Mode)...")
    mcp.run()


def run_ops_mcp_server() -> None:
    mcp = build_ops_mcp_server()
    print("Iniciando MCP Ops Server via STDIO (AI-Readable Mode)...")
    mcp.run()


def run_admin_mcp_server() -> None:
    mcp = build_admin_mcp_server()
    print("Iniciando MCP Admin Server via STDIO (AI-Readable Mode)...")
    mcp.run()
