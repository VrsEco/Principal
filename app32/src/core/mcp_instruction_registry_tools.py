from __future__ import annotations

from typing import Any, Optional

from services.instruction_registry_service import InstructionRegistryService
from src.core.mcp_http_auth import get_http_request_context
from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(
    operation: str,
    *,
    runtime_profile: str | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
) -> MCPResponseMeta:
    tags = ["instruction_registry"]
    if runtime_profile:
        tags.append(f"runtime:{runtime_profile}")
    return MCPResponseMeta(
        domain="mcp_instruction_registry",
        operation=operation,
        scope="mcp_user",
        company_id=company_id,
        user_id=user_id,
        capability=f"mcp_instruction_registry.{operation}",
        permissions=["mcp.instructions.read"],
        tags=tags,
    )


def _success(
    operation: str,
    data: Any,
    *,
    runtime_profile: str | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(
            operation,
            runtime_profile=runtime_profile,
            company_id=company_id,
            user_id=user_id,
        ),
    ).model_dump(mode="json")


def _error(
    operation: str,
    code: str,
    message: str,
    *,
    runtime_profile: str | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=message),
        meta=_meta(
            operation,
            runtime_profile=runtime_profile,
            company_id=company_id,
            user_id=user_id,
        ),
    ).model_dump(mode="json")


def register_instruction_registry_tools(mcp: Any) -> None:
    """Registra tools MCP para discovery e resolução do bundle instrucional mínimo."""

    @mcp.tool()
    def describe_app32_instruction_registry_tool(
        runtime_profile: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Descreve o instruction registry remoto: camadas, canais, runtimes e modelos JSON/YAML do bundle mínimo.
        """
        http_context = dict(get_http_request_context() or {})
        normalized_runtime = str(runtime_profile or http_context.get("runtime_profile") or "squad_cliente").strip().lower()
        company_id = http_context.get("company_id")
        user_id = http_context.get("user_id")

        if runtime_profile and not InstructionRegistryService.supports_runtime(normalized_runtime):
            return _error(
                "instruction_registry.describe",
                "instruction_registry_runtime_not_supported",
                f"Runtime profile não suportado pelo instruction registry: {normalized_runtime}.",
                runtime_profile=normalized_runtime,
                company_id=company_id if isinstance(company_id, int) else None,
                user_id=user_id if isinstance(user_id, int) else None,
            )

        payload = InstructionRegistryService.describe_registry()
        if runtime_profile:
            payload = {
                **payload,
                "runtime_guides": [
                    item
                    for item in payload.get("runtime_guides", [])
                    if item.get("runtime_profile") == normalized_runtime
                ],
            }
        return _success(
            "instruction_registry.describe",
            payload,
            runtime_profile=normalized_runtime,
            company_id=company_id if isinstance(company_id, int) else None,
            user_id=user_id if isinstance(user_id, int) else None,
        )

    @mcp.tool()
    def resolve_app32_instruction_bundle_tool(
        runtime_profile: Optional[str] = None,
        agent_key: Optional[str] = None,
        harness_key: Optional[str] = None,
        channel: Optional[str] = None,
        company_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Resolve o bundle instrucional mínimo, versionado e cacheável do runtime/agent/harness da sessão atual.
        """
        http_context = dict(get_http_request_context() or {})
        normalized_runtime = str(runtime_profile or http_context.get("runtime_profile") or "squad_cliente").strip().lower()
        effective_company_id = company_id or http_context.get("company_id")
        user_id = http_context.get("user_id")
        try:
            bundle = InstructionRegistryService.resolve_bundle(
                runtime_profile=normalized_runtime,
                agent_key=agent_key,
                harness_key=harness_key or str(http_context.get("harness_key") or "").strip() or None,
                channel=str(channel or "stable").strip().lower() or "stable",
                company_id=effective_company_id if isinstance(effective_company_id, int) else None,
            )
        except ValueError as exc:
            return _error(
                "instruction_bundle.resolve",
                "instruction_bundle_invalid_request",
                str(exc),
                runtime_profile=normalized_runtime,
                company_id=effective_company_id if isinstance(effective_company_id, int) else None,
                user_id=user_id if isinstance(user_id, int) else None,
            )

        return _success(
            "instruction_bundle.resolve",
            bundle,
            runtime_profile=normalized_runtime,
            company_id=effective_company_id if isinstance(effective_company_id, int) else None,
            user_id=user_id if isinstance(user_id, int) else None,
        )


__all__ = ["register_instruction_registry_tools"]
