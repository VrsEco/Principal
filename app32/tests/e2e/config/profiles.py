from __future__ import annotations

from dataclasses import dataclass

from app32.tests.e2e.config.environments import (
    E2EEnvironmentSettings,
    E2EExecutionMode,
)


@dataclass(frozen=True)
class ExecutionContract:
    mode: E2EExecutionMode
    destructive_actions_allowed: bool
    requires_isolated_tenant: bool
    require_explicit_company: bool
    summary: str


def build_execution_contract(settings: E2EEnvironmentSettings) -> ExecutionContract:
    summary = (
        f"mode={settings.execution_mode.value}; "
        f"destructive={settings.destructive_actions_allowed}; "
        f"isolated_tenant={settings.requires_isolated_tenant}; "
        f"explicit_company={settings.require_explicit_company}"
    )
    return ExecutionContract(
        mode=settings.execution_mode,
        destructive_actions_allowed=settings.destructive_actions_allowed,
        requires_isolated_tenant=settings.requires_isolated_tenant,
        require_explicit_company=settings.require_explicit_company,
        summary=summary,
    )
