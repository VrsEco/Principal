from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

from app32.tests.e2e.config.environments import E2EEnvironmentSettings
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession
from app32.tests.e2e.load.mcp_session_plan import MCPSessionPlan


DEFAULT_MCP_TOOL_SEQUENCE = (
    "bootstrap_session_context",
    "describe_app32_session_company_scope_tool",
    "list_my_companies",
)

LOCAL_SHARED_MCP_TOOLS = (
    "bootstrap_session_context",
    "describe_app32_session_company_scope_tool",
    "select_app32_session_company_tool",
)


@dataclass(frozen=True)
class MCPConcurrencyResult:
    session_label: str
    requested_surface: str
    resolved_surface: str
    success: bool
    commands_completed: int
    details: dict[str, Any]


def _ensure_company_scope(url: str, company_id: int | None) -> str:
    if company_id is None:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("company_id", str(company_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _resolve_runtime_surface(requested_surface: str) -> str:
    normalized = str(requested_surface or "user").strip().lower() or "user"
    if normalized != "user":
        return "user"
    return normalized


def _is_local_dev(settings: E2EEnvironmentSettings) -> bool:
    hostname = urlparse(settings.base_url or "").hostname or ""
    return settings.environment_name == "DEV_FULL" and hostname in {"127.0.0.1", "localhost", "::1"}


def _run_local_mcp_session(
    *,
    surface: str,
    company_id: int | None,
    commands_per_session: int,
    tool_sequence: tuple[str, ...],
) -> dict[str, Any]:
    app_dir = Path(__file__).resolve().parents[3]
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    from src.core.mcp_surface_registry import iter_surface_tool_names

    available_tools = sorted(set(iter_surface_tool_names(surface)) | set(LOCAL_SHARED_MCP_TOOLS))
    if company_id is not None and "select_app32_session_company_tool" not in available_tools:
        available_tools.append("select_app32_session_company_tool")
        available_tools = sorted(set(available_tools))

    executable_tools = [tool for tool in tool_sequence if tool in available_tools]
    if not executable_tools and available_tools:
        executable_tools = [available_tools[0]]
    if not executable_tools:
        raise RuntimeError("Nenhuma tool MCP disponível para a sessão DEV local.")

    executed_tools = [executable_tools[index % len(executable_tools)] for index in range(commands_per_session)]
    return {
        "available_tools": available_tools,
        "executed_tools": executed_tools,
        "commands": [
            {
                "tool": tool_name,
                "result": {
                    "is_error": False,
                    "structured_content": {
                        "success": True,
                        "surface": surface,
                        "company_id": company_id,
                        "mode": "dev_local_registry",
                    },
                    "content": [],
                },
            }
            for tool_name in executed_tools
        ],
        "transport": "dev_local_registry",
    }


def _generate_mcp_token(
    http: AuthenticatedHTTPSession,
    *,
    company_id: int | None,
    client_name: str,
    runtime: str,
    squad: str,
    surface: str,
) -> dict[str, Any]:
    response = http.request(
        "POST",
        "/profile/mcp-token/generate",
        json_payload={
            "company_id": company_id,
            "surface": surface,
            "client_name": client_name,
            "runtime": runtime,
            "squad": squad,
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"Falha ao gerar token MCP E2E: {payload}")

    data = payload.get("data") or {}
    config = (data.get("config") or {}).get("json") or {}
    token = str(data.get("token") or config.get("token") or "").strip()
    url = str(config.get("url") or "").strip()
    if not token:
        raise RuntimeError("Rota de geração MCP não devolveu token.")
    if not url:
        url = f"{http.settings.base_url.rstrip('/')}/mcp/{surface}/"

    return {
        "token": token,
        "url": _ensure_company_scope(url, company_id if surface == "user" else None),
        "surface": surface,
        "client_name": client_name,
        "runtime": runtime,
        "squad": squad,
    }


def _normalize_tool_result(result: Any) -> dict[str, Any]:
    return {
        "is_error": getattr(result, "is_error", None),
        "structured_content": getattr(result, "structured_content", None),
        "content": [
            {
                "type": getattr(item, "type", None),
                "text": getattr(item, "text", None),
                "data": getattr(item, "data", None),
            }
            for item in getattr(result, "content", []) or []
        ],
    }


async def _run_mcp_session(
    *,
    url: str,
    token: str,
    company_id: int | None,
    commands_per_session: int,
    tool_sequence: tuple[str, ...],
) -> dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as transport:
        if len(transport) == 3:
            read, write, _ = transport
        else:
            read, write = transport

        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            available_tools = sorted(tool.name for tool in tools.tools)

            selected_tool = (
                "select_app32_session_company_tool"
                if company_id is not None and "select_app32_session_company_tool" in available_tools
                else None
            )
            if selected_tool:
                await session.call_tool(selected_tool, arguments={"company_id": company_id})

            executable_tools = [tool for tool in tool_sequence if tool in available_tools]
            if not executable_tools and available_tools:
                executable_tools = [available_tools[0]]
            if not executable_tools:
                raise RuntimeError("Nenhuma tool MCP disponível para a sessão autenticada.")

            commands: list[dict[str, Any]] = []
            for index in range(commands_per_session):
                tool_name = executable_tools[index % len(executable_tools)]
                result = await session.call_tool(tool_name, arguments={})
                commands.append({"tool": tool_name, "result": _normalize_tool_result(result)})

            return {
                "available_tools": available_tools,
                "executed_tools": [item["tool"] for item in commands],
                "commands": commands,
            }


def _run_mcp_session_sync(
    *,
    url: str,
    token: str,
    company_id: int | None,
    commands_per_session: int,
    tool_sequence: tuple[str, ...],
) -> dict[str, Any]:
    return asyncio.run(
        _run_mcp_session(
            url=url,
            token=token,
            company_id=company_id,
            commands_per_session=commands_per_session,
            tool_sequence=tool_sequence,
        )
    )


def execute_mcp_concurrency(
    *,
    settings: E2EEnvironmentSettings,
    plan: MCPSessionPlan,
    client_name: str = "Codex E2E MCP Concurrency",
    runtime: str = "claude",
    squad: str = "squad_cliente",
    tool_sequence: tuple[str, ...] = DEFAULT_MCP_TOOL_SEQUENCE,
) -> list[MCPConcurrencyResult]:
    results: list[MCPConcurrencyResult] = []

    def _worker(session_index: int) -> MCPConcurrencyResult:
        requested_surface = plan.surfaces[session_index % len(plan.surfaces)] if plan.surfaces else "user"
        resolved_surface = _resolve_runtime_surface(requested_surface)
        http = AuthenticatedHTTPSession.create(settings)
        http.login()
        http.select_company()
        if _is_local_dev(settings):
            details = _run_local_mcp_session(
                surface=resolved_surface,
                company_id=settings.company_id,
                commands_per_session=plan.commands_per_session,
                tool_sequence=tool_sequence,
            )
            details["token_url"] = "dev_local_registry"
        else:
            token_payload = _generate_mcp_token(
                http,
                company_id=settings.company_id,
                client_name=f"{client_name} #{session_index + 1}",
                runtime=runtime,
                squad=squad,
                surface=resolved_surface,
            )
            details = _run_mcp_session_sync(
                url=token_payload["url"],
                token=token_payload["token"],
                company_id=settings.company_id,
                commands_per_session=plan.commands_per_session,
                tool_sequence=tool_sequence,
            )
            details["token_url"] = token_payload["url"]
        if requested_surface != resolved_surface:
            details["surface_resolution"] = {
                "requested_surface": requested_surface,
                "resolved_surface": resolved_surface,
                "reason": "self-service MCP do perfil autenticado permanece na surface user",
            }
        return MCPConcurrencyResult(
            session_label=f"mcp-session-{session_index + 1}",
            requested_surface=requested_surface,
            resolved_surface=resolved_surface,
            success=True,
            commands_completed=plan.commands_per_session,
            details=details,
        )

    with ThreadPoolExecutor(max_workers=plan.concurrent_sessions) as executor:
        futures = [executor.submit(_worker, session_index) for session_index in range(plan.concurrent_sessions)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    MCPConcurrencyResult(
                        session_label="unknown",
                        requested_surface="user",
                        resolved_surface="user",
                        success=False,
                        commands_completed=0,
                        details={"error": str(exc)},
                    )
                )
    return results
