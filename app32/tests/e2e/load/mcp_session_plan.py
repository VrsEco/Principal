from __future__ import annotations

from dataclasses import dataclass

from app32.tests.e2e.load.concurrency_profiles import MCPConcurrencyProfile


@dataclass(frozen=True)
class MCPSessionPlan:
    profile_name: str
    concurrent_sessions: int
    commands_per_session: int
    requires_authentication: bool
    tenant_isolation_required: bool
    surfaces: tuple[str, ...]


def build_mcp_session_plan(
    profile: MCPConcurrencyProfile,
    *,
    surfaces: tuple[str, ...] = ("user", "admin", "analytics"),
) -> MCPSessionPlan:
    return MCPSessionPlan(
        profile_name=profile.name,
        concurrent_sessions=profile.concurrent_sessions,
        commands_per_session=profile.commands_per_session,
        requires_authentication=True,
        tenant_isolation_required=True,
        surfaces=surfaces,
    )
