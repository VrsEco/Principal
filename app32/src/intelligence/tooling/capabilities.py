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


def _normalize_scopes(scopes: Iterable[str | ToolScope]) -> tuple[str, ...]:
    normalized: list[str] = []
    for scope in scopes:
        value = scope.value if isinstance(scope, ToolScope) else str(scope)
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized)


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
    "answer_product_help": {
        "domain": "knowledge",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": (),
        "tags": ("read", "product_help", "citations"),
    },
    "search_organizational_knowledge": {
        "domain": "knowledge",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("knowledge.read",),
        "tags": ("read", "search", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "answer_organizational_question": {
        "domain": "knowledge",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("knowledge.read",),
        "tags": ("read", "answer", "citations", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_process_bpmn_activity_tool": {
        "domain": "processes", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("processes.ai_assistant.execute",),
        "tags": ("bpmn", "activity", "data_object", "create"), "required_context": (TOOL_CONTEXT_COMPANY,),
    },
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
    "analyze_process_flow_copilot_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("processes.ai_assistant.view",),
        "tags": ("read", "bpmn", "copilot", "automation"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_process_improvement_requests_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("processes.ai_assistant.view",),
        "tags": ("read", "improvement", "squad_cliente", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_process_improvement_analysis_context_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("processes.ai_assistant.view",),
        "tags": ("read", "analysis", "improvement", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "submit_process_improvement_analysis_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("processes.ai_assistant.execute",),
        "human_gate": True,
        "human_gate_reason": "A sugestão do Squad é persistida para decisão humana na Central de Melhorias.",
        "tags": ("mutation", "analysis", "improvement", "squad_cliente", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "suggest_process_flow_activity_automation_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("processes.ai_assistant.execute",),
        "tags": ("bpmn", "copilot", "automation", "integration"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_process_pop_step_media_context_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("processes.ai_assistant.view",),
        "tags": ("pop", "copilot", "media", "read"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "draft_process_pop_step_description_tool": {
        "domain": "processes",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("processes.ai_assistant.execute",),
        "tags": ("pop", "copilot", "draft", "ai"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_process_pop_step_for_bpmn_tool": {
        "domain": "processes", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("processes.ai_assistant.execute",),
        "tags": ("pop", "bpmn", "create"), "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "attach_process_pop_step_static_image_tool": {
        "domain": "processes", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("processes.ai_assistant.execute",),
        "tags": ("pop", "media", "image", "upload"), "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_plans": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("plan.read",),
        "tags": ("read",),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_plan_diagnostics": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("plan.diagnostics.read",),
        "tags": ("diagnostics",),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_plan_diagnostics_read_model": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("plan.diagnostics.read",),
        "tags": ("read_model", "analytics", "whitelisted"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "update_plan_section": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("plan.section.update",),
        "human_gate": True,
        "human_gate_reason": "Mutação estratégica exige confirmação explícita antes de alterar o plano.",
        "tags": ("crud",),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_global_okr": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("okrs.global.create",),
        "tags": ("crud", "mutation", "tenant_safe", "okr", "global"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_area_okr": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("okrs.area.create",),
        "tags": ("crud", "mutation", "tenant_safe", "okr", "area"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_global_key_result": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("okrs.key_results.create",),
        "tags": ("crud", "mutation", "tenant_safe", "okr", "key_result", "global"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_area_key_result": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("okrs.key_results.create",),
        "tags": ("crud", "mutation", "tenant_safe", "okr", "key_result", "area"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_strategy_identity_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.read",),
        "tags": ("read", "tenant_safe", "identity", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "upsert_strategy_identity_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("strategy.alignment.update",),
        "human_gate": True,
        "human_gate_reason": "Mutação de identidade organizacional estruturada altera insumo estratégico oficial.",
        "tags": ("crud", "mutation", "tenant_safe", "identity", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_process_strategy_profile_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.read",),
        "tags": ("read", "tenant_safe", "process_profile", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "upsert_process_strategy_profile_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("strategy.alignment.update",),
        "human_gate": True,
        "human_gate_reason": "Mutação do perfil estratégico do processo altera insumo de análise estratégica.",
        "tags": ("crud", "mutation", "tenant_safe", "process_profile", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_process_strategy_alignment_links_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.read",),
        "tags": ("read", "tenant_safe", "traceability", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "upsert_process_strategy_alignment_link_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("strategy.alignment.update",),
        "human_gate": True,
        "human_gate_reason": "Mutação de rastreabilidade estratégica impacta diagnósticos e recomendações.",
        "tags": ("crud", "mutation", "tenant_safe", "traceability", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_process_strategy_alignment_link_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("strategy.alignment.update",),
        "human_gate": True,
        "human_gate_reason": "Exclusão de vínculo estratégico remove evidência de rastreabilidade.",
        "tags": ("delete", "mutation", "tenant_safe", "traceability", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_indicator_line_of_sight_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.read",),
        "tags": ("read", "tenant_safe", "indicators", "line_of_sight", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "upsert_indicator_line_of_sight_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("strategy.alignment.update",),
        "human_gate": True,
        "human_gate_reason": "Mutação de linha de visada de indicadores altera leitura de desempenho estratégico.",
        "tags": ("crud", "mutation", "tenant_safe", "indicators", "line_of_sight", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_indicator_line_of_sight_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("strategy.alignment.update",),
        "human_gate": True,
        "human_gate_reason": "Exclusão de linha de visada remove rastreabilidade entre desempenho operacional e corporativo.",
        "tags": ("delete", "mutation", "tenant_safe", "indicators", "line_of_sight", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_strategy_maturation_backlog_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.read",),
        "tags": ("read", "tenant_safe", "maturation", "backlog", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "review_strategy_maturation_item_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("strategy.maturation.review",),
        "human_gate": True,
        "human_gate_reason": "Promoção de item S1-S2 para dado canônico altera a base usada por readiness e análise N1.",
        "tags": ("crud", "mutation", "tenant_safe", "maturation", "human_gate", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_strategy_alignment_n1_readiness_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.analyze",),
        "tags": ("read_model", "analytics", "tenant_safe", "readiness", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_structuring_journey_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("strategy.alignment.read",),
        "tags": ("read_model", "tenant_safe", "journey", "structuring", "maturation"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "run_strategy_alignment_n1_analysis_tool": {
        "domain": "strategy",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("strategy.alignment.analyze",),
        "tags": ("read_model", "analytics", "tenant_safe", "alignment_n1"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_real_estate_auction_settings_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("real_estate_auctions.read",),
        "tags": ("read", "settings", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "upsert_real_estate_auction_settings_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("real_estate_auctions.update",),
        "human_gate": True,
        "human_gate_reason": "Habilitação de módulo por empresa altera superfície funcional do tenant.",
        "tags": ("mutation", "settings", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_real_estate_auction_workspace_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("real_estate_auctions.read",),
        "tags": ("read", "workspace", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_real_estate_auction_properties_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("real_estate_auctions.read",),
        "tags": ("read", "properties", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_real_estate_auction_property_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("real_estate_auctions.read",),
        "tags": ("read", "property_detail", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_real_estate_auction_property_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.create",),
        "human_gate": True,
        "human_gate_reason": "Criação de imóvel/leilão afeta pipeline operacional do tenant.",
        "tags": ("mutation", "create", "properties", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_real_estate_auction_property_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.update",),
        "human_gate": True,
        "human_gate_reason": "Alteração de imóvel/leilão muda a análise financeira e operacional do tenant.",
        "tags": ("mutation", "update", "properties", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "archive_real_estate_auction_property_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("real_estate_auctions.update",),
        "human_gate": True,
        "human_gate_reason": "Arquivamento de imóvel/leilão remove item da operação ativa.",
        "tags": ("mutation", "archive", "properties", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_real_estate_auction_sources_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("real_estate_auctions.read",),
        "tags": ("read", "sources", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_real_estate_auction_source_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.manage_sources",),
        "human_gate": True,
        "human_gate_reason": "Cadastro de fonte altera a malha de captação/importação do tenant.",
        "tags": ("mutation", "create", "sources", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_real_estate_auction_source_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.manage_sources",),
        "human_gate": True,
        "human_gate_reason": "Alteração de fonte impacta a malha de importação/captação do tenant.",
        "tags": ("mutation", "update", "sources", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_real_estate_auction_source_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("real_estate_auctions.manage_sources",),
        "human_gate": True,
        "human_gate_reason": "Remoção de fonte pode interromper fluxos operacionais do tenant.",
        "tags": ("mutation", "delete", "sources", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_real_estate_auction_event_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.edit",),
        "human_gate": True,
        "human_gate_reason": "Inclusão de evento altera a linha do tempo operacional do imóvel.",
        "tags": ("mutation", "create", "events", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_real_estate_auction_event_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.edit",),
        "human_gate": True,
        "human_gate_reason": "Alteração de evento muda o histórico operacional do imóvel.",
        "tags": ("mutation", "update", "events", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_real_estate_auction_event_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("real_estate_auctions.edit",),
        "human_gate": True,
        "human_gate_reason": "Exclusão de evento remove histórico operacional do imóvel.",
        "tags": ("mutation", "delete", "events", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "upsert_real_estate_auction_financial_sheet_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("real_estate_auctions.manage_financial_sheet",),
        "human_gate": True,
        "human_gate_reason": "Ficha financeira afeta decisão econômica e margem do tenant.",
        "tags": ("mutation", "upsert", "financial_sheet", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "upsert_real_estate_auction_due_diligence_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.edit",),
        "human_gate": True,
        "human_gate_reason": "Diligência altera avaliação de posse, risco e operação do imóvel.",
        "tags": ("mutation", "upsert", "due_diligence", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_real_estate_auction_attachment_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("real_estate_auctions.edit",),
        "human_gate": True,
        "human_gate_reason": "Anexos passam a compor o dossiê operacional do imóvel.",
        "tags": ("mutation", "create", "attachments", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_real_estate_auction_attachment_tool": {
        "domain": "real_estate_auctions",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("real_estate_auctions.edit",),
        "human_gate": True,
        "human_gate_reason": "Exclusão de anexo remove evidência do dossiê do imóvel.",
        "tags": ("mutation", "delete", "attachments", "tenant_safe", "client_module"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
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
    "get_company_profile": {
        "domain": "identity_self_service",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("company.profile.read",),
        "tags": ("read", "tenant_safe", "profile"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_company_profile": {
        "domain": "identity_self_service",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("company.profile.update",),
        "tags": ("crud", "mutation", "tenant_safe", "profile"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_company_registration_diagnostics": {
        "domain": "identity_self_service",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("company.profile.read",),
        "tags": ("read", "diagnostics", "tenant_safe", "profile"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
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
    "create_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.write",),
        "tags": ("crud", "tenant_safe", "no_scheduling", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "get_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("meeting.read",),
        "tags": ("read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "update_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.write",),
        "tags": ("crud", "tenant_safe", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_meeting_topic": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "topic", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_meeting_topic": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "topic", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_meeting_topic": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "topic", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_meeting_decision": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "decision", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_meeting_decision": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "decision", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_meeting_decision": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "decision", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "create_meeting_activity": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "activity", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "update_meeting_activity": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "activity", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_meeting_activity": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("crud", "activity", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "sync_meeting_activities_to_project": {
        "domain": "meetings", "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM, "permissions": ("meeting.write",),
        "tags": ("sync", "projects", "activity", "tenant_safe", "quota"), "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "schedule_meeting": {
        "domain": "meetings",
        "scopes": (ToolScope.MCP_ADMIN.value,),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("meeting.schedule",),
        "tags": ("legacy_scheduling", "deprecated"),
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
    "delete_meeting_secure": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("meeting.delete",),
        "human_gate": True,
        "human_gate_reason": "Exclusão de reunião exige confirmação explícita e trilha de auditoria.",
        "tags": ("crud", "hard_delete", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_meetings": {
        "domain": "meetings",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("meeting.read",),
        "tags": ("read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
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
    "create_project": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.create",),
        "tags": ("crud", "tenant_safe", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_projects": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("project.read",),
        "tags": ("read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "update_project": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.update",),
        "tags": ("crud", "tenant_safe", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "delete_project": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("project.delete",),
        "human_gate": True,
        "human_gate_reason": "Soft delete de projeto exige confirmação explícita e trilha de auditoria.",
        "tags": ("crud", "soft_delete", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    },
    "list_project_tasks_secure": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("project.task.read",),
        "tags": ("read", "tenant_safe"),
    },
    "create_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.task.create",),
        "tags": ("crud", "tenant_safe", "quota"),
    },
    "update_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("project.task.update",),
        "tags": ("crud", "tenant_safe", "quota"),
    },
    "delete_project_task_secure": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("project.task.delete",),
        "human_gate": True,
        "human_gate_reason": "Soft delete via MCP exige confirmação explícita e trilha de auditoria.",
        "tags": ("crud", "soft_delete", "quota"),
    },
    "delete_project_task": {
        "domain": "projects",
        "scopes": (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.HIGH,
        "permissions": ("project.task.delete",),
        "human_gate": True,
        "human_gate_reason": "Soft delete via MCP exige confirmação explícita e trilha de auditoria.",
        "tags": ("crud", "soft_delete", "quota"),
        "required_context": (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
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
    "get_work_journey_board_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.board.read",),
        "tags": ("work_journey", "board", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_work_journey_blocks_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.block.read",),
        "tags": ("work_journey", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "save_work_journey_block_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.block.write",),
        "tags": ("work_journey", "crud", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_work_journey_rules_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.rule.read",),
        "tags": ("work_journey", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "save_work_journey_rule_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.rule.write",),
        "tags": ("work_journey", "crud", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "update_work_journey_item_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.item.update",),
        "tags": ("work_journey", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_work_journey_manual_tasks_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.manual_task.read",),
        "tags": ("work_journey", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_work_journey_manual_task_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.manual_task.create",),
        "tags": ("work_journey", "crud", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_work_journey_agenda_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.agenda.read",),
        "tags": ("work_journey", "agenda", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "generate_work_journey_agenda_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.agenda.generate",),
        "tags": ("work_journey", "agenda", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "lock_work_journey_agenda_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.agenda.lock",),
        "tags": ("work_journey", "agenda", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "unlock_work_journey_agenda_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.agenda.unlock",),
        "tags": ("work_journey", "agenda", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "move_work_journey_agenda_item_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.agenda.move",),
        "tags": ("work_journey", "agenda", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_routine_journey_bindings_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.binding.read",),
        "tags": ("work_journey", "binding", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "save_routine_journey_binding_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.binding.write",),
        "tags": ("work_journey", "binding", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_employee_process_routines_for_journey_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.routine.read",),
        "tags": ("work_journey", "routine", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_work_calendar_events_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.calendar.read",),
        "tags": ("work_journey", "calendar", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "create_work_calendar_event_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.calendar.create",),
        "tags": ("work_journey", "calendar", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "update_work_calendar_event_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.calendar.update",),
        "tags": ("work_journey", "calendar", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "delete_work_calendar_event_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.MEDIUM,
        "permissions": ("work_journey.calendar.delete",),
        "tags": ("work_journey", "calendar", "mutation", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "list_work_journey_task_inventory_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.task_inventory.read",),
        "tags": ("work_journey", "task_inventory", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_work_journey_capacity_report_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.capacity.read",),
        "tags": ("work_journey", "capacity", "analytics", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_process_routines_analysis_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.routine_analysis.read",),
        "tags": ("work_journey", "routine_analysis", "analytics", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
    "get_efficiency_collaborators_analysis_tool": {
        "domain": "routine",
        "scopes": (ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        "risk": ToolRiskLevel.LOW,
        "permissions": ("work_journey.efficiency.read",),
        "tags": ("work_journey", "efficiency", "analytics", "read", "tenant_safe"),
        "required_context": (TOOL_CONTEXT_COMPANY,),
    },
}

_STRATEGIC_ALIGNMENT_ALIAS_CAPABILITIES = {
    "get_organizational_identity_tool": "get_strategy_identity_tool",
    "upsert_organizational_identity_tool": "upsert_strategy_identity_tool",
    "get_process_strategic_profile_tool": "get_process_strategy_profile_tool",
    "upsert_process_strategic_profile_tool": "upsert_process_strategy_profile_tool",
    "get_strategic_alignment_n1_readiness_tool": "get_strategy_alignment_n1_readiness_tool",
    "analyze_strategic_alignment_n1_tool": "run_strategy_alignment_n1_analysis_tool",
}

for _alias_tool_name, _canonical_tool_name in _STRATEGIC_ALIGNMENT_ALIAS_CAPABILITIES.items():
    _PRESET_CAPABILITIES[_alias_tool_name] = dict(_PRESET_CAPABILITIES[_canonical_tool_name])


def _register_commercial_capability(
    tool_name: str,
    *,
    domain: str,
    action: str,
    scopes: tuple[str, ...] | None = None,
    risk: ToolRiskLevel | None = None,
    human_gate: bool = False,
    human_gate_reason: str | None = None,
) -> None:
    resolved_scopes = scopes
    if resolved_scopes is None:
        if action == "delete":
            resolved_scopes = (ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value)
        else:
            resolved_scopes = (
                ToolScope.SAPIENS.value,
                ToolScope.MCP_USER.value,
                ToolScope.MCP_ADMIN.value,
            )
    if domain == "finance" and action in {"read", "discover", "analyze"}:
        resolved_scopes = tuple(dict.fromkeys((*resolved_scopes, ToolScope.MCP_ANALYTICS.value)))

    resolved_risk = risk
    if resolved_risk is None:
        if action in {"read", "discover", "analyze"}:
            resolved_risk = ToolRiskLevel.LOW
        elif action == "delete":
            resolved_risk = ToolRiskLevel.HIGH
        else:
            resolved_risk = ToolRiskLevel.MEDIUM

    permission_action = {
        "read": "read",
        "discover": "read",
        "analyze": "read",
        "create": "create",
        "update": "update",
        "delete": "delete",
    }.get(action, "read")

    tags = ["tenant_safe", "commercial", action]
    if domain == "finance":
        tags.append("finance")
    if action in {"create", "update", "delete"}:
        tags.append("mutation")
    else:
        tags.append("read")

    required_context = (TOOL_CONTEXT_COMPANY,)
    if action in {"create", "update", "delete"}:
        required_context = (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY)

    _PRESET_CAPABILITIES[tool_name] = {
        "domain": domain,
        "scopes": resolved_scopes,
        "risk": resolved_risk,
        "permissions": (f"{domain}.{permission_action}",),
        "human_gate": human_gate,
        "human_gate_reason": human_gate_reason,
        "tags": tuple(tags),
        "required_context": required_context,
    }


for _tool_name, _action in (
    ("list_commercial_customer_portfolios", "read"),
    ("create_commercial_customer_portfolio", "create"),
    ("update_commercial_customer_portfolio", "update"),
    ("toggle_commercial_customer_portfolio", "update"),
    ("list_commercial_customers", "read"),
    ("update_commercial_customer", "update"),
    ("list_commercial_issuers", "read"),
    ("create_commercial_issuer", "create"),
    ("update_commercial_issuer", "update"),
    ("list_commercial_catalog_structure", "read"),
    ("create_commercial_catalog_structure_item", "create"),
    ("update_commercial_catalog_structure_item", "update"),
    ("toggle_commercial_catalog_structure_item", "update"),
    ("list_commercial_products_services", "read"),
    ("create_commercial_product_service", "create"),
    ("update_commercial_product_service", "update"),
    ("toggle_commercial_product_service", "update"),
    ("get_commercial_dashboard", "read"),
    ("list_commercial_contracts", "read"),
    ("get_commercial_contract_workspace", "read"),
    ("create_commercial_contract", "create"),
    ("update_commercial_contract_general", "update"),
    ("suspend_commercial_contract", "update"),
    ("close_commercial_contract", "update"),
    ("delete_commercial_contract", "delete"),
    ("add_commercial_contract_item", "create"),
    ("update_commercial_contract_item", "update"),
):
    _register_commercial_capability(
        _tool_name,
        domain="strategy" if _tool_name == "get_commercial_dashboard" else "governance",
        action=_action,
        human_gate=_tool_name in {"suspend_commercial_contract", "close_commercial_contract", "delete_commercial_contract"},
        human_gate_reason=(
            "Mudança de lifecycle contratual exige confirmação explícita e trilha auditável."
            if _tool_name in {"suspend_commercial_contract", "close_commercial_contract", "delete_commercial_contract"}
            else None
        ),
    )

for _tool_name, _action in (
    ("upsert_commercial_contract_financial_terms", "update"),
    ("upsert_commercial_contract_fiscal_terms", "update"),
    ("list_commercial_billing_queue", "read"),
    ("build_commercial_billing_review", "read"),
    ("preview_commercial_billing_batch", "read"),
    ("generate_commercial_billing_batch", "create"),
    ("list_commercial_billings_done", "read"),
    ("generate_commercial_financial_titles_for_billing", "create"),
    ("cancel_commercial_billing", "update"),
    ("list_commercial_fiscal_workspace", "read"),
    ("update_commercial_fiscal_entry", "update"),
    ("assign_commercial_fiscal_batch", "update"),
    ("remove_commercial_fiscal_batch", "update"),
    ("update_commercial_fiscal_status", "update"),
    ("export_commercial_fiscal_integration_spreadsheet", "read"),
):
    _register_commercial_capability(
        _tool_name,
        domain="finance",
        action=_action,
        human_gate=_tool_name in {
            "generate_commercial_billing_batch",
            "generate_commercial_financial_titles_for_billing",
            "cancel_commercial_billing",
        },
        human_gate_reason=(
            "Operação financeira comercial exige confirmação explícita e trilha auditável."
            if _tool_name in {
                "generate_commercial_billing_batch",
                "generate_commercial_financial_titles_for_billing",
                "cancel_commercial_billing",
            }
            else None
        ),
    )

_ALL_MCP_SURFACES: tuple[str, ...] = (
    ToolScope.SAPIENS.value,
    ToolScope.MCP_USER.value,
    ToolScope.MCP_ADMIN.value,
    ToolScope.MCP_ANALYTICS.value,
    ToolScope.MCP_OPS.value,
)


def _register_mcp_support_capability(
    tool_name: str,
    *,
    domain: str = "governance",
    action: str = "read",
    scopes: tuple[str, ...] | None = None,
    risk: ToolRiskLevel | None = None,
    permissions: tuple[str, ...] | None = None,
    human_gate: bool = False,
    human_gate_reason: str | None = None,
    tags: tuple[str, ...] = (),
    required_context: tuple[str, ...] | None = None,
) -> None:
    is_mutation = action in {"create", "update", "delete", "approve", "execute", "review"}
    resolved_risk = risk or (
        ToolRiskLevel.HIGH
        if action == "delete"
        else ToolRiskLevel.MEDIUM
        if is_mutation
        else ToolRiskLevel.LOW
    )
    resolved_permissions = permissions or (f"{domain}.{'delete' if action == 'delete' else 'update' if is_mutation else 'read'}",)
    resolved_context = required_context
    if resolved_context is None:
        resolved_context = (TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY) if is_mutation else ()
    resolved_scopes = scopes or _ALL_MCP_SURFACES

    _PRESET_CAPABILITIES[tool_name] = {
        "domain": domain,
        "scopes": _normalize_scopes(resolved_scopes),
        "risk": resolved_risk,
        "permissions": resolved_permissions,
        "human_gate": human_gate,
        "human_gate_reason": human_gate_reason,
        "tags": tuple(dict.fromkeys(("tenant_safe", "mcp_support", action, *tags))),
        "required_context": resolved_context,
    }


for _tool_name in (
    "bootstrap_session_context",
    "list_feature_catalog",
    "get_feature_guide",
    "get_feature_examples",
    "get_feature_constraints",
    "describe_app32_analysis_catalog_tool",
    "describe_app32_crud_contracts_tool",
    "describe_app32_domain_examples_tool",
    "describe_app32_domain_playbooks_tool",
    "describe_app32_external_ai_onboarding_tool",
    "describe_app32_external_llm_factory_surface_tool",
    "describe_app32_implantation_persona_profile_tool",
    "describe_app32_instruction_registry_tool",
    "resolve_app32_instruction_bundle_tool",
    "describe_app32_operational_readiness_tool",
    "describe_app32_permission_matrix_tool",
    "describe_app32_profile_contracts_tool",
    "describe_app32_release_checklist_tool",
    "describe_app32_sapiens_factory_tool",
    "trace_app32_capability_dependencies_tool",
    "describe_app32_available_sapiens_squads_tool",
    "describe_app32_session_company_scope_tool",
    "describe_app32_squad_runtime_tool",
    "describe_app32_surface_playbooks_tool",
    "describe_app32_tool_freeze_procedure_tool",
    "describe_app32_usage_dashboard_tool",
    "list_app32_integrations_catalog",
):
    _register_mcp_support_capability(_tool_name, tags=("catalog", "read"))

for _tool_name in (
    "describe_app32_session_harness_tool",
    "select_app32_session_harness_tool",
    "resolve_app32_operation_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        domain="identity_self_service",
        action="read",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        risk=ToolRiskLevel.LOW,
        permissions=("identity_self_service.read",),
        tags=("routing", "session", "read"),
    )

for _tool_name in (
    "preview_app32_implantation_persona_profile_update_tool",
    "assess_app32_change_request_tool",
    "evaluate_app32_external_llm_factory_session_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        action="analyze",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        risk=ToolRiskLevel.MEDIUM,
        permissions=("governance.read",),
        tags=("assessment",),
    )

for _tool_name in (
    "apply_app32_implantation_persona_profile_update_tool",
    "resolve_app32_sapiens_activation_tool",
    "select_app32_session_company_tool",
    "clear_app32_session_company_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        action="update",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        risk=ToolRiskLevel.MEDIUM,
        permissions=("governance.update",),
        human_gate=_tool_name in {
            "apply_app32_implantation_persona_profile_update_tool",
            "resolve_app32_sapiens_activation_tool",
        },
        human_gate_reason=(
            "Atualização de runtime/persona Sapiens exige confirmação explícita."
            if _tool_name
            in {"apply_app32_implantation_persona_profile_update_tool", "resolve_app32_sapiens_activation_tool"}
            else None
        ),
        tags=("mutation", "session"),
    )



def _register_consultive_capability(tool_name: str, *, action: str = "read", write: bool = False) -> None:
    _register_mcp_support_capability(
        tool_name,
        domain="consultive",
        action=action,
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        risk=ToolRiskLevel.MEDIUM if write else ToolRiskLevel.LOW,
        permissions=("consultive.write",) if write else ("consultive.read",),
        human_gate=write,
        human_gate_reason="Registro ou conversão consultiva exige validação humana e trilha auditável." if write else None,
        required_context=(TOOL_CONTEXT_COMPANY,),
        tags=(
            "consultive",
            "assisted_analysis",
            "mcp_first",
            *(("explicit_human_confirmation",) if tool_name in {
                "consultive_register_assisted_analysis",
                "consultive_register_squad_validation",
                "consultive_register_consultant_decision",
            } else ()),
        ),
    )


for _tool_name in (
    "consultive_get_next_action",
    "consultive_get_front_context",
    "consultive_get_front_evidence",
    "consultive_get_front_gaps",
    "consultive_get_methodology_guidance",
    "consultive_resolve_protocol",
    "consultive_list_assisted_analyses",
):
    _register_consultive_capability(_tool_name, action="read", write=False)

for _tool_name in (
    "consultive_register_assisted_analysis",
    "consultive_register_squad_validation",
):
    _register_consultive_capability(_tool_name, action="review", write=True)

for _tool_name in (
    "consultive_upsert_protocol",
    "consultive_register_consultant_decision",
    "consultive_create_recommended_action",
):
    _register_consultive_capability(_tool_name, action="create", write=True)

_register_mcp_support_capability(
    "request_new_app32_integration",
    domain="operations",
    action="create",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_OPS.value, ToolScope.MCP_ADMIN.value),
    risk=ToolRiskLevel.MEDIUM,
    permissions=("support.escalate",),
    tags=("integration", "backlog"),
)

_register_mcp_support_capability(
    "get_incentive_indicators",
    domain="finance",
    action="read",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
    risk=ToolRiskLevel.LOW,
    permissions=("finance.read",),
    required_context=(TOOL_CONTEXT_COMPANY,),
    tags=("incentives", "read"),
)

for _tool_name, _action in (
    ("get_strategic_connection_graph", "read"),
    ("generate_strategic_connection_summary", "analyze"),
):
    _register_mcp_support_capability(
        _tool_name,
        domain="analytics",
        action=_action,
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_ANALYTICS.value),
        risk=ToolRiskLevel.LOW,
        permissions=("analytics.read",),
        required_context=(TOOL_CONTEXT_COMPANY,),
        tags=("strategic_connections", "incentives", "read_model", "tenant_safe"),
    )

# Projeção estritamente read-only dos vínculos estratégicos já cadastrados. Ela
# segue o mesmo contrato RBAC das demais leituras de alinhamento do Squad Cliente.
_register_mcp_support_capability(
    "get_strategic_connection_metrics",
    domain="strategy",
    action="read",
    scopes=(
        ToolScope.SAPIENS.value,
        ToolScope.MCP_USER.value,
        ToolScope.MCP_ADMIN.value,
        ToolScope.MCP_ANALYTICS.value,
    ),
    risk=ToolRiskLevel.LOW,
    permissions=("strategy.alignment.read",),
    required_context=(TOOL_CONTEXT_COMPANY,),
    tags=("strategic_connections", "incentives", "read_model", "tenant_safe", "empty_safe"),
)

_register_mcp_support_capability(
    "create_sector_okr_structure_tool",
    domain="strategy",
    action="create",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
    risk=ToolRiskLevel.MEDIUM,
    permissions=("okrs.area.create", "okrs.key_results.create", "project.create"),
    human_gate=True,
    human_gate_reason="Cadastro de OKRs setoriais, resultados-chave e projetos exige confirmação humana explícita.",
    required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    tags=("strategy", "sector_structure", "transactional", "explicit_human_confirmation"),
)

_register_mcp_support_capability(
    "sync_plan_participants_tool",
    domain="strategy",
    action="create",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
    risk=ToolRiskLevel.MEDIUM,
    permissions=("plan.participants.create", "plan.section.update"),
    human_gate=True,
    human_gate_reason="Inclusão de participantes e definição do owner do planejamento exigem confirmação humana explícita.",
    required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    tags=("strategy", "planning", "participants", "transactional", "explicit_human_confirmation"),
)

_register_mcp_support_capability(
    "create_single_plan_driver_tool",
    domain="strategy",
    action="create",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
    risk=ToolRiskLevel.MEDIUM,
    permissions=("plan.section.update",),
    human_gate=True,
    human_gate_reason="Cadastro e conclusão do direcionador estratégico exigem confirmação humana explícita.",
    required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    tags=("strategy", "planning", "driver", "transactional", "explicit_human_confirmation"),
)

_register_mcp_support_capability(
    "create_and_link_plan_global_okrs_tool",
    domain="strategy",
    action="create",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
    risk=ToolRiskLevel.MEDIUM,
    permissions=("okrs.global.create", "okrs.area.update", "plan.section.update"),
    human_gate=True,
    human_gate_reason="Criação de OKRs Globais e vínculo aos OKRs de Área exigem confirmação humana explícita.",
    required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    tags=("strategy", "planning", "global_okr", "transactional", "explicit_human_confirmation"),
)

_register_mcp_support_capability(
    "correct_plan_global_okrs_tool",
    domain="strategy",
    action="update",
    scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
    risk=ToolRiskLevel.MEDIUM,
    permissions=("okrs.global.update", "okrs.area.update", "plan.section.update"),
    human_gate=True,
    human_gate_reason="Correção de OKRs Globais e de seus vínculos setoriais exige confirmação humana explícita.",
    required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
    tags=("strategy", "planning", "global_okr", "correction", "transactional", "explicit_human_confirmation"),
)

for _tool_name in (
    "list_work_journey_absences_tool",
    "list_work_journey_transfers_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        domain="routine",
        action="read",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value, ToolScope.MCP_ANALYTICS.value),
        permissions=("work_journey.read",),
        required_context=(TOOL_CONTEXT_COMPANY,),
        tags=("work_journey", "read"),
    )

for _tool_name in (
    "create_work_journey_absence_request_tool",
    "create_work_journey_transfer_request_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        domain="routine",
        action="create",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value),
        permissions=("work_journey.create",),
        tags=("work_journey", "mutation"),
    )

for _tool_name in (
    "approve_work_journey_absence_request_tool",
    "approve_work_journey_transfer_request_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        domain="routine",
        action="update",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        risk=ToolRiskLevel.MEDIUM,
        permissions=("work_journey.approve",),
        human_gate=True,
        human_gate_reason="Aprovação de ausência/transferência altera a jornada operacional e exige confirmação.",
        tags=("work_journey", "approval", "mutation"),
    )

for _tool_name in (
    "delete_work_journey_block_tool",
    "delete_work_journey_rule_tool",
    "delete_work_journey_manual_task_tool",
):
    _register_mcp_support_capability(
        _tool_name,
        domain="routine",
        action="delete",
        scopes=(ToolScope.SAPIENS.value, ToolScope.MCP_ADMIN.value),
        risk=ToolRiskLevel.HIGH,
        permissions=("work_journey.delete",),
        human_gate=True,
        human_gate_reason="Exclusão de jornada operacional exige confirmação explícita e trilha auditável.",
        tags=("work_journey", "delete"),
    )

_DOMAIN_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("consultive", "consultive"),
    ("consultivo", "consultive"),
    ("assisted_analysis", "consultive"),
    ("billing", "finance"),
    ("fiscal", "finance"),
    ("process", "processes"),
    ("auction", "real_estate_auctions"),
    ("real_estate", "real_estate_auctions"),
    ("leil", "real_estate_auctions"),
    ("plan", "strategy"),
    ("meeting", "meetings"),
    ("journey", "routine"),
    ("absence", "routine"),
    ("transfer", "routine"),
    ("task", "routine"),
    ("work", "routine"),
    ("project", "projects"),
    ("user", "identity"),
    ("company", "governance"),
    ("issuer", "governance"),
    ("portfolio", "governance"),
    ("customer", "governance"),
    ("commercial", "governance"),
    ("contract", "governance"),
    ("catalog", "governance"),
    ("registry", "governance"),
    ("permission", "governance"),
    ("surface", "governance"),
    ("profile", "governance"),
    ("readiness", "governance"),
    ("release", "governance"),
    ("usage", "governance"),
    ("squad", "governance"),
    ("session_company", "governance"),
    ("persona", "governance"),
    ("finance", "finance"),
    ("financial", "finance"),
    ("incentive", "finance"),
    ("rule", "governance"),
    ("technical", "operations"),
    ("diagnostic", "operations"),
    ("query", "analytics"),
)

_DOMAIN_FILTER_ALIASES: dict[str, tuple[str, ...]] = {}

_FINANCE_READ_PREFIXES = (
    "list_",
    "get_",
)
_FINANCE_CREATE_PREFIXES = (
    "create_",
    "generate_",
    "process_",
    "reconcile_",
    "classify_",
    "match_",
    "apply_",
    "dispatch_",
    "duplicate_",
    "import_",
    "ask_",
    "resolve_",
    "convert_",
    "replace_",
    "suggest_",
    "ai_rank_",
)
_FINANCE_UPDATE_PREFIXES = (
    "update_",
    "toggle_",
    "upsert_",
    "review_",
)


def _expand_domain_aliases(domains: set[str]) -> set[str]:
    expanded = expand_tool_domain_aliases(str(domain) for domain in domains)
    for domain in tuple(expanded):
        expanded.update(_DOMAIN_FILTER_ALIASES.get(domain, ()))
    return expanded


def infer_tool_action(tool_name: str, domain: str | None = None) -> str | None:
    lowered = str(tool_name or "").strip().lower()
    normalized_domain = normalize_tool_domain(domain) if domain else None

    if lowered in {
        "delete_meeting_topic",
        "delete_meeting_decision",
        "delete_meeting_activity",
    }:
        # Remoções de itens JSON pertencem à atualização da reunião; não apagam
        # a reunião nem ProjectTask já sincronizada.
        return "update"

    if lowered == "review_strategy_maturation_item_tool":
        return "review"
    if lowered in {
        "resolve_app32_instruction_bundle_tool",
        "resolve_app32_operation_tool",
    }:
        return "read"

    if normalized_domain == "consultive":
        if lowered in {
            "consultive_register_assisted_analysis",
            "consultive_register_squad_validation",
        }:
            return "review"
        if lowered.startswith(("consultive_get_", "consultive_list_")):
            return "read"
        if lowered.startswith("consultive_resolve_"):
            return "read"
        if lowered.startswith("consultive_upsert_"):
            return "update"
        if lowered.startswith(("consultive_register_", "consultive_create_")):
            return "create"
        return "analyze"

    if normalized_domain == "finance":
        if lowered.startswith(_FINANCE_READ_PREFIXES):
            return "read"
        if lowered.startswith(_FINANCE_UPDATE_PREFIXES):
            return "update"
        if lowered.startswith(_FINANCE_CREATE_PREFIXES):
            return "create"

    prefix_map = (
        ("list_", "read"),
        ("get_", "read"),
        ("describe_", "read"),
        ("search_", "discover"),
        ("create_", "create"),
        ("update_", "update"),
        ("toggle_", "update"),
        ("upsert_", "update"),
        ("replace_", "update"),
        ("review_", "update"),
        ("move_", "update"),
        ("complete_", "update"),
        ("finish_", "update"),
        ("start_", "update"),
        ("send_", "create"),
        ("request_", "create"),
        ("schedule_", "create"),
        ("log_", "create"),
        ("register_", "create"),
        ("delete_", "delete"),
        ("restore_", "update"),
        ("generate_", "analyze"),
        ("simulate_", "analyze"),
        ("analyze_", "analyze"),
        ("query_", "analyze"),
        ("dispatch_", "execute"),
        ("apply_", "execute"),
        ("process_", "execute"),
        ("reconcile_", "execute"),
        ("classify_", "execute"),
        ("convert_", "execute"),
        ("match_", "execute"),
        ("import_", "execute"),
        ("duplicate_", "create"),
        ("ask_", "create"),
        ("resolve_", "update"),
    )
    for prefix, action in prefix_map:
        if lowered.startswith(prefix):
            return action
    return None


def _infer_financial_tool_capability(tool_name: str, description: str) -> ToolCapability:
    action = infer_tool_action(tool_name, "finance") or "read"
    is_read_only = action in {"read", "discover", "analyze"}
    scopes: tuple[str, ...]
    if is_read_only:
        scopes = (
            ToolScope.SAPIENS.value,
            ToolScope.MCP_USER.value,
            ToolScope.MCP_ADMIN.value,
            ToolScope.MCP_ANALYTICS.value,
        )
    else:
        scopes = (
            ToolScope.SAPIENS.value,
            ToolScope.MCP_USER.value,
            ToolScope.MCP_ADMIN.value,
        )

    permission_action = {
        "read": "view",
        "discover": "view",
        "analyze": "view",
        "create": "create",
        "update": "edit",
        "execute": "create",
        "delete": "delete",
    }.get(action, "view")

    risk = ToolRiskLevel.LOW if is_read_only else ToolRiskLevel.MEDIUM
    human_gate = False
    human_gate_reason = None
    if action == "delete":
        risk = ToolRiskLevel.HIGH
        human_gate = True
        human_gate_reason = "Exclusão financeira exige confirmação explícita e trilha auditável."

    tags = ["finance", "tenant_safe"]
    if is_read_only:
        tags.append("read")
    else:
        tags.extend(("mutation", action))

    return ToolCapability(
        name=tool_name,
        domain="finance",
        description=description,
        scopes=scopes,
        risk=risk,
        permissions=(f"financial.{permission_action}",),
        human_gate=human_gate,
        human_gate_reason=human_gate_reason,
        tags=tuple(tags),
        required_context=(TOOL_CONTEXT_COMPANY,),
    )


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

    if domain == "finance":
        return _infer_financial_tool_capability(tool_name, description)

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
