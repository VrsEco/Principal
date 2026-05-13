from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .runtime_profiles import get_runtime_profile_spec, normalize_runtime_profile


@dataclass(frozen=True)
class McpChannelGateRequest:
    surface: str
    runtime_profile: str | None = None
    actor_type: str | None = None
    mcp_enabled: bool = True
    training_completed: bool = True


@dataclass(frozen=True)
class McpChannelGateDecision:
    allowed: bool
    reason: str
    checks: tuple[str, ...]
    resolved_runtime_profile: str | None = None
    resolved_actor_type: str | None = None


def _deny(
    reason: str,
    checks: Sequence[str],
    *,
    runtime_profile: str | None = None,
    actor_type: str | None = None,
) -> McpChannelGateDecision:
    return McpChannelGateDecision(
        allowed=False,
        reason=reason,
        checks=tuple(checks),
        resolved_runtime_profile=runtime_profile,
        resolved_actor_type=actor_type,
    )


def _allow(
    checks: Sequence[str],
    *,
    runtime_profile: str | None = None,
    actor_type: str | None = None,
) -> McpChannelGateDecision:
    return McpChannelGateDecision(
        allowed=True,
        reason="ok",
        checks=tuple(checks),
        resolved_runtime_profile=runtime_profile,
        resolved_actor_type=actor_type,
    )


def evaluate_mcp_channel_gate(request: McpChannelGateRequest) -> McpChannelGateDecision:
    checks: list[str] = ["mcp_channel_gate"]
    normalized_surface = str(request.surface or "").strip().lower() or "user"
    normalized_runtime_profile = normalize_runtime_profile(request.runtime_profile)
    spec = get_runtime_profile_spec(normalized_runtime_profile)

    if not request.mcp_enabled:
        return _deny(
            "usuário não habilitado para operação MCP",
            (*checks, "mcp_disabled"),
            runtime_profile=normalized_runtime_profile,
            actor_type=request.actor_type,
        )

    resolved_actor_type = str(request.actor_type or "").strip().lower() or None
    if spec is not None:
        checks.append("runtime_profile_spec")
        if normalized_surface != spec.default_surface:
            return _deny(
                f"runtime_profile {spec.key} exige surface {spec.default_surface}",
                (*checks, "runtime_profile_surface_mismatch"),
                runtime_profile=spec.key,
                actor_type=resolved_actor_type or spec.actor_type,
            )
        if spec.requires_training and not request.training_completed:
            return _deny(
                "usuário MCP ainda não concluiu habilitação/treinamento obrigatório",
                (*checks, "runtime_profile_training_required"),
                runtime_profile=spec.key,
                actor_type=resolved_actor_type or spec.actor_type,
            )
        return _allow(
            (*checks, "mcp_channel_gate_allowed"),
            runtime_profile=spec.key,
            actor_type=resolved_actor_type or spec.actor_type,
        )

    return _allow(
        (*checks, "mcp_channel_gate_allowed_without_profile"),
        runtime_profile=normalized_runtime_profile,
        actor_type=resolved_actor_type,
    )


__all__ = [
    "McpChannelGateDecision",
    "McpChannelGateRequest",
    "evaluate_mcp_channel_gate",
]
