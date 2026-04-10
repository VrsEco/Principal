from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_OPERATIONAL_READINESS_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, selector: str | None = None) -> MCPResponseMeta:
    return MCPResponseMeta(
        domain="mcp_operational_readiness",
        operation=operation,
        scope="mcp_admin",
        capability=f"mcp_operational_readiness.{operation}",
        permissions=["mcp.operational_readiness.read"],
        tags=["readiness", "operations", "go-live", *(["selector:" + selector] if selector else [])],
    )


def register_operational_readiness_tools(mcp: Any) -> None:
    @mcp.tool()
    def describe_app32_operational_readiness_tool(
        phase: Optional[str] = None,
        gate_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Descreve a readiness operacional para abertura controlada de uso IA/MCP."""

        if gate_id:
            gate = APP32_OPERATIONAL_READINESS_MANIFEST.get_gate(gate_id)
            if gate is None:
                return MCPErrorEnvelope(
                    error=MCPErrorDetail(
                        code="operational_readiness_gate_not_found",
                        message=f"Gate de readiness não encontrado: {gate_id}.",
                    ),
                    meta=_meta("operational_readiness.describe", selector=gate_id.strip().lower()),
                ).model_dump(mode="json")

            return MCPSuccessEnvelope[Any](
                data=gate.model_dump(mode="json"),
                meta=_meta("operational_readiness.describe", selector=gate.gate_id),
            ).model_dump(mode="json")

        if phase:
            gates = APP32_OPERATIONAL_READINESS_MANIFEST.get_phase(phase)
            if not gates:
                return MCPErrorEnvelope(
                    error=MCPErrorDetail(
                        code="operational_readiness_phase_not_found",
                        message=f"Fase de readiness não encontrada: {phase}.",
                    ),
                    meta=_meta("operational_readiness.describe", selector=phase.strip().lower()),
                ).model_dump(mode="json")

            return MCPSuccessEnvelope[Any](
                data=[gate.model_dump(mode="json") for gate in gates],
                meta=_meta("operational_readiness.describe", selector=phase.strip().lower()),
            ).model_dump(mode="json")

        return MCPSuccessEnvelope[Any](
            data=APP32_OPERATIONAL_READINESS_MANIFEST.model_dump(mode="json"),
            meta=_meta("operational_readiness.describe"),
        ).model_dump(mode="json")


__all__ = ["register_operational_readiness_tools"]
