from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


TOOL_CONTEXT_USER = "user"
TOOL_CONTEXT_COMPANY = "company"

from src.intelligence.taxonomy import expand_tool_domain_aliases, normalize_tool_domain


class ToolScope(str, Enum):
    """Escopos operacionais suportados pelo APP32."""

    SAPIENS = "sapiens"
    MCP_USER = "mcp_user"
    MCP_ADMIN = "mcp_admin"
    MCP_ANALYTICS = "mcp_analytics"
    MCP_OPS = "mcp_ops"


class ToolRiskLevel(str, Enum):
    """Nível de risco para uso por agentes e integrações MCP."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ToolCapability:
    """Metadados de segurança e descoberta para uma tool do APP32."""

    name: str
    domain: str
    description: str
    scopes: tuple[str, ...]
    risk: ToolRiskLevel
    permissions: tuple[str, ...] = field(default_factory=tuple)
    human_gate: bool = False
    human_gate_reason: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    required_context: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "scopes": list(self.scopes),
            "risk": self.risk.value,
            "permissions": list(self.permissions),
            "human_gate": self.human_gate,
            "human_gate_reason": self.human_gate_reason,
            "tags": list(self.tags),
            "required_context": list(self.required_context),
        }

    def matches_scope(self, scope: str | ToolScope | None) -> bool:
        if scope is None:
            return True
        normalized = scope.value if isinstance(scope, ToolScope) else str(scope)
        return normalized in self.scopes

    def matches_domain(self, domain: str | Sequence[str] | None) -> bool:
        if domain is None:
            return True
        if isinstance(domain, str):
            return self.domain in _expand_domain_aliases({domain})
        return self.domain in _expand_domain_aliases(set(domain))


_PRESET_CAPABILITIES: dict[str, dict[str, Any]] = {
    "consult_rules": {
        "domain": "governance",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("governance.read",),
        "tags": ("policy", "reference"),
    },
    "query_database": {
        "domain": "analytics",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("analytics.query", "db.read"),
        "human_gate": True,
        "human_gate_reason": "Executa consulta SQL livre para análise e exige controle reforçado.",
        "tags": ("sql", "analysis"),
    },
    "escalate_technical_issue": {
        "domain": "operations",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_OPS.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("support.escalate",),
        "tags": ("support", "incident"),
    },
    "request_engineering_suggestion": {
        "domain": "operations",
        "scopes": (
            ToolScope.SAPIENS.value,
            ToolScope.MCP_USER.value,
            ToolScope.MCP_ADMIN.value,
            ToolScope.MCP_OPS.value,
        ),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("engineering.suggestion.create",),
        "tags": ("support", "backlog", "mutation"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_my_engineering_suggestions": {
        "domain": "operations",
        "scopes": (
            ToolScope.SAPIENS.value,
            ToolScope.MCP_USER.value,
            ToolScope.MCP_ADMIN.value,
            ToolScope.MCP_OPS.value,
        ),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("engineering.suggestion.read_self",),
        "tags": ("support", "backlog", "read"),
        "required_context": (TOOL_CONTEXT_USER,),
    },
    "create_process_area": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("process.area.create",),
        "tags": ("crud",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_macro_process": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("process.macro.create",),
        "tags": ("crud",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_macro_process": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("process.macro.update",),
        "tags": ("crud", "mutation"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_process": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("process.create",),
        "human_gate": True,
        "human_gate_reason": "Criação de processo impacta execução operacional e rastreabilidade.",
        "tags": ("crud", "mutation"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_company_status": {
        "domain": "governance",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("company.status.update",),
        "human_gate": True,
        "human_gate_reason": "Atualização de status corporativo é operação administrativa sensível.",
        "tags": ("admin",),
    },
    "list_process_hierarchy": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("process.read",),
        "tags": ("read",),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_plans": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("plan.read",),
        "tags": ("read",),
    },
    "get_plan_diagnostics": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("plan.diagnostics.read",),
        "tags": ("diagnostics",),
    },
    "get_plan_diagnostics_read_model": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("plan.diagnostics.read",),
        "tags": ("read_model", "analytics", "whitelisted"),
    },
    "update_plan_section": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("plan.section.update",),
        "human_gate": False,
        "tags": ("crud",),
    },
    "get_my_work": {
        "domain": "routine",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work.read_self",),
        "tags": ("personal", "read"),
        "required_context": (TOOL_CONTEXT_USER,),
    },
    "list_my_companies": {
        "domain": "identity_self_service",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("identity.read",),
        "tags": ("read",),
        "required_context": (TOOL_CONTEXT_USER,),
    },
    "list_system_users": {
        "domain": "identity_admin",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("user.admin.read",),
        "human_gate": True,
        "human_gate_reason": "Listagem de usuários do sistema é operação administrativa.",
        "tags": ("admin",),
    },
    "register_system_user": {
        "domain": "identity_admin",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.CRITICAL,
        "permissions": ("user.admin.create",),
        "human_gate": True,
        "human_gate_reason": "Cadastro de usuário do sistema exige validação humana e trilha de auditoria.",
        "tags": ("admin", "mutation"),
    },
    "get_financial_results": {
        "domain": "finance",
        "scopes": (
            ToolScope.SAPIENS.value,
            ToolScope.MCP_ADMIN.value,
            ToolScope.MCP_ANALYTICS.value,
        ),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("financial.results.read",),
        "tags": ("finance", "read", "executive"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "update_user_contacts": {
        "domain": "identity_self_service",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("user.contacts.update",),
        "tags": ("crud",),
    },
    "schedule_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.schedule",),
        "tags": ("crud",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "start_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.start",),
        "tags": ("workflow",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "log_meeting_discussion": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("meeting.notes.write",),
        "tags": ("notes",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "finish_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.finish",),
        "tags": ("workflow",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "send_meeting_minutes": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.minutes.send",),
        "tags": ("communication",),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_tasks_today": {
        "domain": "routine",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("task.read",),
        "tags": ("read",),
    },
    "create_project_task": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.task.create",),
        "tags": ("crud",),
    },
    "list_project_tasks_secure": {
        "domain": "projects",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("project.task.read",),
        "tags": ("read", "tenant_safe"),
    },
    "create_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.task.create",),
        "tags": ("crud", "tenant_safe", "quota"),
    },
    "update_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.task.update",),
        "tags": ("crud", "tenant_safe", "quota"),
    },
    "delete_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.MCP_ADMIN.value,),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("project.task.delete",),
        "human_gate": True,
        "human_gate_reason": "Soft delete via MCP exige confirmação explícita e trilha de auditoria.",
        "tags": ("crud", "soft_delete", "quota"),
    },
    "restore_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.MCP_ADMIN.value,),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("project.task.restore",),
        "human_gate": True,
        "human_gate_reason": "Restauração de item soft-deletado exige confirmação explícita.",
        "tags": ("restore", "soft_delete", "quota"),
    },
    "get_project_task_analytics_report": {
        "domain": "projects",
        "scopes": (ToolScope.MCP_ANALYTICS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("project.task.analyze",),
        "tags": ("analytics", "read", "soft_delete"),
    },
    "complete_task": {
        "domain": "routine",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("task.complete",),
        "tags": ("mutation",),
    },
    "log_work_hours": {
        "domain": "routine",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("worklog.create",),
        "tags": ("crud",),
    },
    "request_deadline_extension": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("deadline.extension.request",),
        "human_gate": False,
        "tags": ("workflow",),
    },
    "list_team_workload": {
        "domain": "workload",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value, ToolScope.MCP_OPS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("workload.read",),
        "tags": ("analytics", "read"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_team_workload_read_model": {
        "domain": "workload",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("workload.read",),
        "tags": ("analytics", "read_model", "whitelisted"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_projects_execution_risk_read_model": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("projects.analytics.read",),
        "tags": ("analytics", "read_model", "whitelisted"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
}

_DOMAIN_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("process", "processes"),
    ("plan", "strategy"),
    ("meeting", "meetings"),
    ("task", "routine"),
    ("work", "routine"),
    ("project", "projects"),
    ("user", "identity"),
    ("company", "governance"),
    ("finance", "finance"),
    ("rule", "governance"),
    ("technical", "operations"),
    ("diagnostic", "operations"),
    ("query", "analytics"),
)

_DOMAIN_FILTER_ALIASES: dict[str, tuple[str, ...]] = {}


def _normalize_scopes(scopes: Iterable[str | ToolScope]) -> tuple[str, ...]:
    normalized: list[str] = []
    for scope in scopes:
        value = scope.value if isinstance(scope, ToolScope) else str(scope)
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def _expand_domain_aliases(domains: set[str]) -> set[str]:
    expanded = expand_tool_domain_aliases(str(domain) for domain in domains)
    for domain in tuple(expanded):
        expanded.update(_DOMAIN_FILTER_ALIASES.get(domain, ()))
    return expanded


def infer_tool_capability(tool: Any) -> ToolCapability:
    """Deriva metadados mínimos de segurança para uma tool desconhecida."""

    tool_name = getattr(tool, "name", str(tool))
    description = getattr(tool, "description", "") or ""
    preset = _PRESET_CAPABILITIES.get(tool_name)
    if preset:
        return ToolCapability(
            name=tool_name,
            domain=preset["domain"],
            description=description,
            scopes=_normalize_scopes(preset["scopes"]),
            risk=preset["risk"],
            permissions=tuple(preset.get("permissions", ())),
            human_gate=bool(preset.get("human_gate", False)),
            human_gate_reason=preset.get("human_gate_reason"),
            tags=tuple(preset.get("tags", ())),
            required_context=tuple(preset.get("required_context", ())),
        )

    lowered = tool_name.lower()
    domain = "general"
    for keyword, mapped_domain in _DOMAIN_KEYWORDS:
        if keyword in lowered:
            domain = mapped_domain
            break
    domain = normalize_tool_domain(domain) or "general"

    mutating_prefixes = ("create_", "update_", "delete_", "complete_", "log_", "request_", "start_", "finish_", "send_", "register_")
    is_mutation = lowered.startswith(mutating_prefixes)
    is_adminish = any(keyword in lowered for keyword in ("admin", "system", "schema", "diagnostic"))

    risk = ToolRiskLevel.MEDIUM if is_mutation else ToolRiskLevel.LOW
    if "query" in lowered or "diagnostic" in lowered or "schema" in lowered:
        risk = ToolRiskLevel.HIGH if is_mutation else ToolRiskLevel.MEDIUM
    if is_adminish:
        risk = ToolRiskLevel.HIGH if risk in (ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM) else risk

    scopes = (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value)
    if domain == "analytics":
        scopes = (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value)
    elif domain == "operations":
        scopes = (ToolScope.SAPIENS.value, ToolScope.MCP_OPS.value)
    if is_adminish or risk in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
        scopes = (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value)

    permission_domain = domain.replace("-", "_")
    return ToolCapability(
        name=tool_name,
        domain=domain,
        description=description,
        scopes=scopes,
        risk=risk,
        permissions=(f"{permission_domain}.use",),
        human_gate=risk in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL),
        human_gate_reason="Risco alto/administrativo inferido automaticamente." if risk in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL) else None,
        tags=("inferred",),
        required_context=(TOOL_CONTEXT_COMPANY,),
    )


def build_capability_index(tools: Iterable[Any]) -> dict[str, ToolCapability]:
    """Cria o índice de capacidades a partir das tools disponíveis."""

    index: dict[str, ToolCapability] = {}
    for tool in tools:
        capability = infer_tool_capability(tool)
        index[capability.name] = capability
    return index


def _filter_capabilities(
    capabilities: Iterable[ToolCapability],
    *,
    scope: str | ToolScope | Sequence[str | ToolScope] | None = None,
    domain: str | Sequence[str] | None = None,
) -> list[ToolCapability]:
    scope_values: tuple[str, ...] | None = None
    if scope is not None:
        if isinstance(scope, (str, ToolScope)):
            scope_values = _normalize_scopes((scope,))
        else:
            scope_values = _normalize_scopes(scope)

    domain_values: set[str] | None = None
    if domain is not None:
        if isinstance(domain, str):
            domain_values = _expand_domain_aliases({domain})
        else:
            domain_values = _expand_domain_aliases(set(domain))

    result: list[ToolCapability] = []
    for capability in capabilities:
        if scope_values is not None and not any(item in capability.scopes for item in scope_values):
            continue
        if domain_values is not None and capability.domain not in domain_values:
            continue
        result.append(capability)
    return result


def build_capability_manifest(
    capabilities: Iterable[ToolCapability],
    *,
    scope: str | ToolScope | Sequence[str | ToolScope] | None = None,
    domain: str | Sequence[str] | None = None,
    include_tools: bool = True,
) -> dict[str, Any]:
    """Monta um manifesto consumível por agentes para descoberta de capacidades."""

    filtered = _filter_capabilities(capabilities, scope=scope, domain=domain)
    sorted_capabilities = sorted(filtered, key=lambda item: (item.domain, item.name))
    manifest: dict[str, Any] = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "capabilities": len(sorted_capabilities),
            "domains": len({cap.domain for cap in sorted_capabilities}),
            "scopes": sorted({scope for cap in sorted_capabilities for scope in cap.scopes}),
        },
        "domains": {},
        "scopes": {},
    }

    if include_tools:
        manifest["tools"] = [cap.to_dict() for cap in sorted_capabilities]

    for capability in sorted_capabilities:
        manifest["domains"].setdefault(capability.domain, []).append(capability.name)
        for item in capability.scopes:
            manifest["scopes"].setdefault(item, []).append(capability.name)

    return manifest
