from __future__ import annotations

from copy import deepcopy
from typing import Any


class SapiensFactoryRegistryService:
    """Registry consultivo da factory para descoberta e rastreamento de dependências."""

    _CAPABILITIES: tuple[dict[str, Any], ...] = (
        {
            "key": "sapiens_factory_change_assessment",
            "title": "Assessment de mudança técnica",
            "domain": "engineering",
            "description": "Classifica pedidos técnicos, identifica camadas afetadas e propõe próximo passo seguro.",
            "layers": ["service", "tool_contract", "rest_mcp", "workflow", "ui_sapiens"],
            "dependencies": [
                "sapiens_factory_registry",
                "sapiens_factory_governance",
            ],
            "artifacts": [
                "change_intent_form",
                "governance_risk_report",
                "change_plan_outline",
            ],
            "status": "ready",
        },
        {
            "key": "sapiens_factory_registry",
            "title": "Registry de capacidades da factory",
            "domain": "engineering",
            "description": "Mapeia capacidades, dependências e superfícies canônicas do APP32.",
            "layers": ["service", "rest_mcp", "ui_sapiens"],
            "dependencies": [],
            "artifacts": ["capability_trace", "surface_manifest"],
            "status": "ready",
        },
        {
            "key": "sapiens_factory_governance",
            "title": "Governança e human gate da factory",
            "domain": "governance",
            "description": "Aplica risco, RBAC, tenant-scope e confirmação explícita por operação.",
            "layers": ["service", "tool_contract", "rest_mcp", "workflow"],
            "dependencies": [],
            "artifacts": ["policy_decision", "audit_event", "human_gate_matrix"],
            "status": "ready",
        },
        {
            "key": "external_llm_factory_surface",
            "title": "Surface externa LLM para factory",
            "domain": "integration",
            "description": "Surface MCP/API externa para clientes como Codex/CLI operarem a factory com segurança.",
            "layers": ["rest_mcp", "workflow", "ui_sapiens"],
            "dependencies": [
                "sapiens_factory_change_assessment",
                "sapiens_factory_governance",
            ],
            "artifacts": ["external_surface_manifest", "client_onboarding_guide"],
            "status": "ready",
        },
        {
            "key": "financial_results_query",
            "title": "Consulta de resultados financeiros",
            "domain": "finance",
            "description": "Vertical piloto read-only para resumir resultado financeiro do tenant com evidências.",
            "layers": ["service", "tool_contract", "rest_mcp", "workflow", "ui_sapiens"],
            "dependencies": ["sapiens_factory_change_assessment"],
            "artifacts": ["financial_results_summary", "financial_results_tool_contract"],
            "status": "pilot",
        },
    )

    @classmethod
    def list_capabilities(cls) -> list[dict[str, Any]]:
        return [deepcopy(item) for item in cls._CAPABILITIES]

    @classmethod
    def get_capability(cls, capability_key: str) -> dict[str, Any] | None:
        normalized = str(capability_key or "").strip().lower()
        for item in cls._CAPABILITIES:
            if item["key"] == normalized:
                return deepcopy(item)
        return None

    @classmethod
    def trace_capability_dependencies(cls, capability_key: str) -> dict[str, Any]:
        capability = cls.get_capability(capability_key)
        if capability is None:
            return {"found": False, "capability": None, "dependencies": []}
        dependencies = [
            dep for dep in (cls.get_capability(dep_key) for dep_key in capability.get("dependencies", []))
            if dep is not None
        ]
        return {"found": True, "capability": capability, "dependencies": dependencies}

    @classmethod
    def build_registry_snapshot(cls) -> dict[str, Any]:
        capabilities = cls.list_capabilities()
        by_domain: dict[str, int] = {}
        for item in capabilities:
            domain = str(item.get("domain") or "unknown")
            by_domain[domain] = by_domain.get(domain, 0) + 1
        return {
            "summary": {
                "capabilities": len(capabilities),
                "domains": len(by_domain),
                "pilot_capabilities": sum(1 for item in capabilities if item.get("status") == "pilot"),
            },
            "domain_distribution": by_domain,
            "capabilities": capabilities,
        }
