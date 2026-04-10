from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from src.core.mcp_surface_registry import get_surface_manifest, normalize_surface
from src.intelligence.mcp_contracts import (
    APP32_PROFILE_CONTRACTS_MANIFEST,
    APP32_SURFACE_PLAYBOOKS_MANIFEST,
)
from src.intelligence.security.runtime import RuntimeSecuritySnapshot, build_runtime_security_snapshot
from src.intelligence.security.tool_policy import (
    ToolPolicyDecision,
    ToolPolicyRequest,
    evaluate_tool_policy,
)
from src.intelligence.tool_catalog import catalog


_ROLE_PLAYBOOK_ALIASES = {
    "administrador_tecnico": "admin_tecnico",
}


@dataclass(frozen=True)
class SimulatedAgentScenario:
    scenario_id: str
    user_id: int
    role: str
    surface: str
    tool_name: str
    domain: str
    action: str
    requested_company_id: int | None = None
    accessible_company_ids: tuple[int, ...] = ()
    employee_id: int | None = None
    permissions: tuple[str, ...] = ()
    risk: str | None = None
    confirmed_mutation: bool = False
    channel: str = "simulated"
    thread_id: str = "simulated-harness"
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SimulatedAgentHarnessResult:
    scenario: SimulatedAgentScenario
    allowed: bool
    reason: str
    resolved_surface: str
    resolved_company_id: int | None
    runtime_security: RuntimeSecuritySnapshot
    policy_decision: ToolPolicyDecision
    tool_in_surface_manifest: bool
    profile_contract_found: bool
    surface_playbook_found: bool
    checks: tuple[str, ...] = field(default_factory=tuple)

    def to_summary(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario.scenario_id,
            "allowed": self.allowed,
            "reason": self.reason,
            "surface": self.resolved_surface,
            "resolved_company_id": self.resolved_company_id,
            "tool_name": self.scenario.tool_name,
            "domain": self.scenario.domain,
            "action": self.scenario.action,
            "tool_in_surface_manifest": self.tool_in_surface_manifest,
            "profile_contract_found": self.profile_contract_found,
            "surface_playbook_found": self.surface_playbook_found,
            "checks": list(self.checks),
            "policy": self.policy_decision.to_audit_event(),
            "runtime_security": self.runtime_security.to_metadata(),
        }


def _normalize_playbook_role(role: str) -> str:
    normalized = str(role or "").strip().lower()
    return _ROLE_PLAYBOOK_ALIASES.get(normalized, normalized)


def evaluate_simulated_agent_scenario(
    scenario: SimulatedAgentScenario,
    *,
    surface_manifest_loader=get_surface_manifest,
) -> SimulatedAgentHarnessResult:
    """Avalia um cenário simulado de agente sem LLM nem execução real de tools."""

    resolved_surface = normalize_surface(scenario.surface)
    checks: list[str] = ["normalize_surface"]

    runtime_security = build_runtime_security_snapshot(
        user_id=scenario.user_id,
        requested_company_id=scenario.requested_company_id,
        channel=scenario.channel,
        thread_id=scenario.thread_id,
        role=scenario.role,
        employee_id=scenario.employee_id,
        accessible_company_ids=scenario.accessible_company_ids,
        permissions=scenario.permissions,
        metadata=scenario.metadata,
    )
    checks.append("runtime_security_snapshot")

    profile_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(scenario.role)
    profile_contract_found = profile_contract is not None
    if profile_contract_found:
        checks.append("profile_contract")

    surface_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface(resolved_surface)
    surface_playbook_found = surface_playbook is not None
    if surface_playbook_found:
        checks.append("surface_playbook")

    manifest = surface_manifest_loader(resolved_surface, include_tools=True)
    manifest_tool_names = {tool["name"] for tool in manifest.get("tools", [])}
    tool_in_surface_manifest = scenario.tool_name in manifest_tool_names
    checks.append("surface_manifest")

    capability = catalog.get_tool_capability(scenario.tool_name)
    resolved_risk = scenario.risk or (getattr(getattr(capability, "risk", None), "value", None) or "medium")
    resolved_permissions = scenario.permissions or tuple(getattr(capability, "permissions", ()) or ())

    policy_decision = evaluate_tool_policy(
        {
            "user_id": scenario.user_id,
            "company_id": runtime_security.principal.company_id,
            "employee_id": scenario.employee_id,
            "role": scenario.role,
            "channel": scenario.channel,
            "thread_id": scenario.thread_id,
            "permissions": scenario.permissions,
            "metadata": dict(scenario.metadata or {}),
        },
        ToolPolicyRequest(
            tool_name=scenario.tool_name,
            surface=resolved_surface,
            domain=scenario.domain,
            action=scenario.action,
            risk=resolved_risk,
            requested_company_id=scenario.requested_company_id,
            accessible_company_ids=runtime_security.accessible_company_ids,
            required_permissions=tuple(resolved_permissions),
            confirmed_mutation=scenario.confirmed_mutation,
            metadata=scenario.metadata,
        ),
    )
    checks.append("tool_policy")

    if not profile_contract_found:
        return SimulatedAgentHarnessResult(
            scenario=scenario,
            allowed=False,
            reason="perfil MCP não suportado",
            resolved_surface=resolved_surface,
            resolved_company_id=runtime_security.resolved_company_id,
            runtime_security=runtime_security,
            policy_decision=policy_decision,
            tool_in_surface_manifest=tool_in_surface_manifest,
            profile_contract_found=False,
            surface_playbook_found=surface_playbook_found,
            checks=tuple((*checks, "profile_contract_missing")),
        )

    if not surface_playbook_found:
        return SimulatedAgentHarnessResult(
            scenario=scenario,
            allowed=False,
            reason=f"surface playbook ausente para {resolved_surface}",
            resolved_surface=resolved_surface,
            resolved_company_id=runtime_security.resolved_company_id,
            runtime_security=runtime_security,
            policy_decision=policy_decision,
            tool_in_surface_manifest=tool_in_surface_manifest,
            profile_contract_found=True,
            surface_playbook_found=False,
            checks=tuple((*checks, "surface_playbook_missing")),
        )

    normalized_role_for_playbook = _normalize_playbook_role(runtime_security.principal.role)
    if normalized_role_for_playbook not in set(surface_playbook.actor_roles):
        return SimulatedAgentHarnessResult(
            scenario=scenario,
            allowed=False,
            reason=f"perfil {normalized_role_for_playbook} não previsto no playbook da surface {resolved_surface}",
            resolved_surface=resolved_surface,
            resolved_company_id=runtime_security.resolved_company_id,
            runtime_security=runtime_security,
            policy_decision=policy_decision,
            tool_in_surface_manifest=tool_in_surface_manifest,
            profile_contract_found=True,
            surface_playbook_found=True,
            checks=tuple((*checks, "surface_playbook_role_mismatch")),
        )

    if scenario.domain not in set(surface_playbook.allowed_domains):
        return SimulatedAgentHarnessResult(
            scenario=scenario,
            allowed=False,
            reason=f"domínio {scenario.domain} não permitido na surface {resolved_surface}",
            resolved_surface=resolved_surface,
            resolved_company_id=runtime_security.resolved_company_id,
            runtime_security=runtime_security,
            policy_decision=policy_decision,
            tool_in_surface_manifest=tool_in_surface_manifest,
            profile_contract_found=True,
            surface_playbook_found=True,
            checks=tuple((*checks, "surface_playbook_domain_mismatch")),
        )

    if not tool_in_surface_manifest:
        return SimulatedAgentHarnessResult(
            scenario=scenario,
            allowed=False,
            reason=f"tool {scenario.tool_name} não pertence ao manifest da surface {resolved_surface}",
            resolved_surface=resolved_surface,
            resolved_company_id=runtime_security.resolved_company_id,
            runtime_security=runtime_security,
            policy_decision=policy_decision,
            tool_in_surface_manifest=False,
            profile_contract_found=True,
            surface_playbook_found=True,
            checks=tuple((*checks, "tool_not_in_surface_manifest")),
        )

    if not policy_decision.allowed:
        return SimulatedAgentHarnessResult(
            scenario=scenario,
            allowed=False,
            reason=policy_decision.reason,
            resolved_surface=resolved_surface,
            resolved_company_id=policy_decision.resolved_company_id,
            runtime_security=runtime_security,
            policy_decision=policy_decision,
            tool_in_surface_manifest=True,
            profile_contract_found=True,
            surface_playbook_found=True,
            checks=tuple((*checks, *policy_decision.checks)),
        )

    return SimulatedAgentHarnessResult(
        scenario=scenario,
        allowed=True,
        reason="ok",
        resolved_surface=resolved_surface,
        resolved_company_id=policy_decision.resolved_company_id,
        runtime_security=runtime_security,
        policy_decision=policy_decision,
        tool_in_surface_manifest=True,
        profile_contract_found=True,
        surface_playbook_found=True,
        checks=tuple((*checks, *policy_decision.checks, "simulated_scope_allowed")),
    )


__all__ = [
    "SimulatedAgentHarnessResult",
    "SimulatedAgentScenario",
    "evaluate_simulated_agent_scenario",
]
