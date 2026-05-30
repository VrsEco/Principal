from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeTarget:
    key: str
    route: str
    purpose: str
    expected_url_fragment: str
    readiness_selector: str


SMOKE_TARGETS: tuple[SmokeTarget, ...] = (
    SmokeTarget("auth.login", "/login", "entrada de autenticação", "/login", "#loginForm"),
    SmokeTarget("workspace.my_work", "/my-work", "workspace principal", "/my-work", "body"),
    SmokeTarget("meetings.root_redirect", "/meetings/", "entrada de reuniões", "/meetings/company/", ".meeting-management"),
    SmokeTarget("integrations.api_mcp", "/api-mcp", "catálogo de integrações", "/api-mcp", "#integrationsWorkspace"),
    SmokeTarget("integrations.channels", "/channels", "configurações de canais", "/channels", "#integrationsContainer"),
)
