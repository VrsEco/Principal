from __future__ import annotations

from typing import Any, Optional

from services.mcp_connection_snippet_service import MCPConnectionSnippetService
from services.squad_runtime_bootstrap_service import SquadRuntimeBootstrapService
from src.core.mcp_http_auth import get_http_actor_role, get_http_request_context
from src.intelligence.mcp_contracts import (
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


def _meta(operation: str, *, runtime_profile: str | None = None, surface: str | None = None) -> MCPResponseMeta:
    tags = ["squad_runtime"]
    if runtime_profile:
        tags.append(f"runtime:{runtime_profile}")
    if surface:
        tags.append(f"surface:{surface}")
    return MCPResponseMeta(
        domain="mcp_squad_runtime",
        operation=operation,
        scope=f"mcp_{surface or 'user'}",
        actor_role=get_http_actor_role(),
        capability=f"mcp_squad_runtime.{operation}",
        permissions=["mcp.squad_runtime.read"],
        tags=tags,
    )


def _success(operation: str, data: Any, *, runtime_profile: str | None = None, surface: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, runtime_profile=runtime_profile, surface=surface),
    ).model_dump(mode="json")


def _error(operation: str, code: str, message: str, *, runtime_profile: str | None = None, surface: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=message),
        meta=_meta(operation, runtime_profile=runtime_profile, surface=surface),
    ).model_dump(mode="json")


def register_squad_runtime_tools(mcp: Any) -> None:
    """Registra bootstrap operacional resumido dos squads para runtimes externos."""

    @mcp.tool()
    def describe_app32_squad_runtime_tool(
        runtime_profile: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retorna bootstrap operacional resumido do squad/runtine, pronto para orientar o CLI.
        """
        http_context = dict(get_http_request_context() or {})
        normalized_runtime = str(
            runtime_profile
            or http_context.get("runtime_profile")
            or "squad_cliente"
        ).strip().lower()
        surface = str(http_context.get("surface") or "user").strip().lower()

        if normalized_runtime == "squad_cliente":
            startup_tools = list(
                dict.fromkeys(
                    [
                        "describe_app32_squad_runtime_tool",
                        *MCPConnectionSnippetService.RUNTIME_PROFILES["squad_cliente"]["startup_tools"],
                    ]
                )
            )
            data = SquadRuntimeBootstrapService.build_squad_cliente_bootstrap(
                startup_tools=startup_tools,
            )
            return _success(
                "squad_runtime.describe",
                data,
                runtime_profile="squad_cliente",
                surface=surface,
            )

        runtime_spec = get_runtime_profile_spec(normalized_runtime)
        if runtime_spec is None:
            return _error(
                "squad_runtime.describe",
                "squad_runtime_not_found",
                f"Runtime profile inválido ou não encontrado: {normalized_runtime}.",
                runtime_profile=normalized_runtime,
                surface=surface,
            )

        data = {
            "runtime_profile": runtime_spec.key,
            "canonical_label": runtime_spec.label,
            "surface": runtime_spec.default_surface,
            "default_harness_key": runtime_spec.default_harness_key,
            "default_harness_label": runtime_spec.default_harness_label,
            "harnesses": [
                {
                    "key": harness.key,
                    "label": harness.label,
                    "business_role": harness.business_role,
                }
                for harness in runtime_spec.harnesses
            ],
        }
        return _success(
            "squad_runtime.describe",
            data,
            runtime_profile=runtime_spec.key,
            surface=surface,
        )


__all__ = ["register_squad_runtime_tools"]
