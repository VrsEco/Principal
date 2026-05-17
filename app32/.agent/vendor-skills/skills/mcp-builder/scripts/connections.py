"""Lightweight connection handling for MCP servers."""

import asyncio
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
import logging
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class MCPConnection(ABC):
    """Base class for MCP server connections."""

    def __init__(self):
        self.session = None
        self._stack = None

    @abstractmethod
    def _create_context(self):
        """Create the connection context based on connection type."""

    async def _open(self):
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        try:
            ctx = self._create_context()
            result = await self._stack.enter_async_context(ctx)

            if len(result) == 2:
                read, write = result
            elif len(result) == 3:
                read, write, _ = result
            else:
                raise ValueError(f"Unexpected context result: {result}")

            session_ctx = ClientSession(read, write)
            self.session = await self._stack.enter_async_context(session_ctx)
            await self.session.initialize()
        except BaseException:
            await self._stack.__aexit__(None, None, None)
            self.session = None
            self._stack = None
            raise

    async def __aenter__(self):
        """Initialize MCP server connection."""
        await self._open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up MCP server connection resources."""
        if self._stack:
            await self._stack.__aexit__(exc_type, exc_val, exc_tb)
        self.session = None
        self._stack = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """Retrieve available tools from the MCP server."""
        response = await self.session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server with provided arguments."""
        result = await self.session.call_tool(tool_name, arguments=arguments)
        return result.content


class MCPConnectionStdio(MCPConnection):
    """MCP connection using standard input/output."""

    def __init__(self, command: str, args: list[str] = None, env: dict[str, str] = None):
        super().__init__()
        self.command = command
        self.args = args or []
        self.env = env

    def _create_context(self):
        return stdio_client(
            StdioServerParameters(command=self.command, args=self.args, env=self.env)
        )


class MCPConnectionSSE(MCPConnection):
    """MCP connection using Server-Sent Events."""

    def __init__(self, url: str, headers: dict[str, str] = None):
        super().__init__()
        self.url = url
        self.headers = headers or {}

    def _create_context(self):
        return sse_client(url=self.url, headers=self.headers)


class MCPConnectionHTTP(MCPConnection):
    """MCP connection using Streamable HTTP."""

    def __init__(
        self,
        url: str,
        headers: dict[str, str] = None,
        *,
        reconnect_attempts: int = 2,
        reconnect_backoff_seconds: float = 0.25,
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.reconnect_attempts = max(1, int(reconnect_attempts))
        self.reconnect_backoff_seconds = max(0.0, float(reconnect_backoff_seconds))
        self._reconnect_lock = asyncio.Lock()

    def _create_context(self):
        return streamablehttp_client(url=self.url, headers=self.headers)

    @staticmethod
    def _is_invalid_session_error(exc: Exception) -> bool:
        message = str(exc or "").strip().lower()
        return any(
            marker in message
            for marker in (
                "no valid session id provided",
                "invalid or expired session id",
                "missing session id",
            )
        )

    async def _reconnect(self) -> None:
        async with self._reconnect_lock:
            if self._stack:
                await self._stack.__aexit__(None, None, None)
            self.session = None
            self._stack = None
            await self._open()

    async def _call_with_reconnect(self, operation_name: str, callback):
        last_exc: Exception | None = None
        for attempt in range(1, self.reconnect_attempts + 1):
            try:
                return await callback()
            except Exception as exc:
                last_exc = exc
                if not self._is_invalid_session_error(exc) or attempt >= self.reconnect_attempts:
                    raise
                logger.warning(
                    "Sessão streamable-HTTP inválida em %s; reinitializando sessão e repetindo chamada (tentativa %s/%s).",
                    operation_name,
                    attempt,
                    self.reconnect_attempts,
                )
                await self._reconnect()
                if self.reconnect_backoff_seconds > 0:
                    await asyncio.sleep(self.reconnect_backoff_seconds * attempt)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"Falha inesperada ao executar {operation_name}")

    async def list_tools(self) -> list[dict[str, Any]]:
        return await self._call_with_reconnect("list_tools", super().list_tools)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return await self._call_with_reconnect(
            f"call_tool:{tool_name}",
            lambda: super(MCPConnectionHTTP, self).call_tool(tool_name, arguments),
        )


def create_connection(
    transport: str,
    command: str = None,
    args: list[str] = None,
    env: dict[str, str] = None,
    url: str = None,
    headers: dict[str, str] = None,
) -> MCPConnection:
    """Factory function to create the appropriate MCP connection.

    Args:
        transport: Connection type ("stdio", "sse", or "http")
        command: Command to run (stdio only)
        args: Command arguments (stdio only)
        env: Environment variables (stdio only)
        url: Server URL (sse and http only)
        headers: HTTP headers (sse and http only)

    Returns:
        MCPConnection instance
    """
    transport = transport.lower()

    if transport == "stdio":
        if not command:
            raise ValueError("Command is required for stdio transport")
        return MCPConnectionStdio(command=command, args=args, env=env)

    elif transport == "sse":
        if not url:
            raise ValueError("URL is required for sse transport")
        return MCPConnectionSSE(url=url, headers=headers)

    elif transport in ["http", "streamable_http", "streamable-http"]:
        if not url:
            raise ValueError("URL is required for http transport")
        return MCPConnectionHTTP(url=url, headers=headers)

    else:
        raise ValueError(f"Unsupported transport type: {transport}. Use 'stdio', 'sse', or 'http'")
