from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserConcurrencyProfile:
    name: str
    concurrent_users: int
    iterations_per_user: int
    description: str


@dataclass(frozen=True)
class MCPConcurrencyProfile:
    name: str
    concurrent_sessions: int
    commands_per_session: int
    description: str


USER_CONCURRENCY_PROFILES = {
    "baseline": UserConcurrencyProfile(
        name="baseline",
        concurrent_users=5,
        iterations_per_user=3,
        description="concorrência mínima para validação local e homologação leve",
    ),
    "high": UserConcurrencyProfile(
        name="high",
        concurrent_users=30,
        iterations_per_user=10,
        description="concorrência alta para stress funcional com muitos usuários logados",
    ),
}

MCP_CONCURRENCY_PROFILES = {
    "baseline": MCPConcurrencyProfile(
        name="baseline",
        concurrent_sessions=3,
        commands_per_session=5,
        description="sessões MCP simultâneas mínimas para validação de isolamento",
    ),
    "high": MCPConcurrencyProfile(
        name="high",
        concurrent_sessions=15,
        commands_per_session=20,
        description="alto paralelismo MCP com múltiplas superfícies e contexto autenticado",
    ),
}
