from __future__ import annotations

from typing import Any

from services.sapiens_factory_registry_service import SapiensFactoryRegistryService
from services.sapiens_factory_service import SapiensFactoryService
from src.intelligence.mcp_contracts import APP32_SAPIENS_FACTORY_MANIFEST, MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def _meta(operation: str) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="sapiens_factory",
        operation=operation,
        scope="mcp_admin",
        capability=f"sapiens_factory.{operation}",
        permissions=["factory.admin.read"],
        tags=["factory", "engineering", "governance"],
        human_gate_required=False,
    )


def register_sapiens_factory_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_sapiens_factory_tool() -> dict[str, Any]:
        """Descreve o manifesto consultivo da Sapiens Factory."""
        return MCPSuccessEnvelope[Any](
            data=APP32_SAPIENS_FACTORY_MANIFEST.model_dump(mode="json"),
            meta=_meta("describe"),
            message="Manifesto consultivo da Sapiens Factory.",
        ).model_dump(mode="json")

    @mcp.tool()
    def assess_app32_change_request_tool(
        request_text: str,
        change_type: str | None = None,
        target_object: str | None = None,
        domain: str | None = None,
        execution_mode: str = "diagnose",
        urgency: str = "medium",
    ) -> dict[str, Any]:
        """Classifica um pedido técnico e propõe os próximos passos da Sapiens Factory."""
        assessment = SapiensFactoryService.assess_change_request(
            {
                "request_text": request_text,
                "change_type": change_type,
                "target_object": target_object,
                "domain": domain,
                "execution_mode": execution_mode,
                "urgency": urgency,
            }
        )
        return MCPSuccessEnvelope[Any](
            data=assessment,
            meta=_meta("assess_change"),
            message="Assessment inicial do pedido técnico.",
        ).model_dump(mode="json")

    @mcp.tool()
    def trace_app32_capability_dependencies_tool(capability_key: str) -> dict[str, Any]:
        """Traça a capability e suas dependências na registry da Sapiens Factory."""
        trace = SapiensFactoryRegistryService.trace_capability_dependencies(capability_key)
        if not trace.get("found"):
            return MCPErrorEnvelope(
                error=MCPErrorDetail(
                    code="factory_capability_not_found",
                    message="Capability não encontrada na registry da Sapiens Factory.",
                    details={"capability_key": capability_key},
                ),
                meta=_meta("trace_dependencies"),
            ).model_dump(mode="json")
        return MCPSuccessEnvelope[Any](
            data=trace,
            meta=_meta("trace_dependencies"),
            message="Rastro de dependências da capability.",
        ).model_dump(mode="json")
