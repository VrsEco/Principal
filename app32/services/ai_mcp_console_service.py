from __future__ import annotations

from collections import Counter
from typing import Any

from src.core.mcp_surface_registry import get_surface_manifest
from src.intelligence.mcp_contracts.domain_playbooks import APP32_DOMAIN_PLAYBOOKS_MANIFEST
from src.intelligence.mcp_contracts.external_ai_onboarding import APP32_EXTERNAL_AI_ONBOARDING_MANIFEST
from src.intelligence.mcp_contracts.operational_readiness import APP32_OPERATIONAL_READINESS_MANIFEST
from src.intelligence.mcp_contracts.permission_matrix import APP32_PERMISSION_MATRIX_MANIFEST
from src.intelligence.mcp_contracts.playbooks import APP32_SURFACE_PLAYBOOKS_MANIFEST
from src.intelligence.mcp_contracts.profiles import APP32_PROFILE_CONTRACTS_MANIFEST
from src.intelligence.mcp_contracts.release_checklist import APP32_RELEASE_CHECKLIST_MANIFEST
from src.intelligence.mcp_contracts.tool_freeze import APP32_TOOL_FREEZE_MANIFEST
from src.intelligence.mcp_contracts.usage_dashboard import APP32_USAGE_DASHBOARD_MANIFEST
from src.intelligence.tool_catalog import catalog


class AIMCPConsoleService:
    """Monta o estado consultivo do console operacional IA/MCP."""

    SURFACES = ("user", "admin", "analytics", "ops")

    @classmethod
    def build_frontend_state(cls, active_company: Any | None = None) -> dict[str, Any]:
        profiles = [profile.model_dump(mode="json") for profile in APP32_PROFILE_CONTRACTS_MANIFEST.profiles]
        surfaces = [playbook.model_dump(mode="json") for playbook in APP32_SURFACE_PLAYBOOKS_MANIFEST.playbooks]
        domains = [playbook.model_dump(mode="json") for playbook in APP32_DOMAIN_PLAYBOOKS_MANIFEST.playbooks]
        permissions = [matrix.model_dump(mode="json") for matrix in APP32_PERMISSION_MATRIX_MANIFEST.matrices]
        onboarding = APP32_EXTERNAL_AI_ONBOARDING_MANIFEST.model_dump(mode="json")
        release = APP32_RELEASE_CHECKLIST_MANIFEST.model_dump(mode="json")
        freeze = APP32_TOOL_FREEZE_MANIFEST.model_dump(mode="json")
        dashboard = APP32_USAGE_DASHBOARD_MANIFEST.model_dump(mode="json")
        readiness = APP32_OPERATIONAL_READINESS_MANIFEST.model_dump(mode="json")

        capability_manifest = catalog.get_capability_manifest(include_tools=True)
        capability_tools = sorted(
            list(capability_manifest.get("tools", [])),
            key=lambda item: (str(item.get("domain", "")), str(item.get("name", ""))),
        )

        surface_capabilities = []
        for surface in cls.SURFACES:
            manifest = get_surface_manifest(surface, include_tools=True)
            tools = list(manifest.get("tools", []))
            surface_capabilities.append(
                {
                    "surface": surface,
                    "tool_count": len(tools),
                    "domains": sorted({tool.get("domain") for tool in tools if tool.get("domain")}),
                    "human_gate_count": sum(1 for tool in tools if tool.get("human_gate")),
                    "critical_count": sum(1 for tool in tools if tool.get("risk") == "critical"),
                }
            )

        risk_counter = Counter(tool.get("risk") for tool in capability_tools if tool.get("risk"))
        domain_counter = Counter(tool.get("domain") for tool in capability_tools if tool.get("domain"))

        readiness_by_phase = []
        for phase in ("contracts", "release", "onboarding", "operations", "go_live"):
            gates = [gate for gate in readiness["gates"] if gate["phase"] == phase]
            readiness_by_phase.append(
                {
                    "phase": phase,
                    "gate_count": len(gates),
                    "required_count": sum(1 for gate in gates if gate["status"] == "required"),
                    "gates": gates,
                }
            )

        configuration_links = [
            {
                "title": "Console Operacional IA/MCP",
                "href": "/configs/ai/mcp",
                "description": "Governança, onboarding, readiness, catálogo e observabilidade em uma única superfície.",
                "kind": "console",
            },
            {
                "title": "Parâmetros gerais de IA",
                "href": "/configs/ai",
                "description": "Configurar agentes, parâmetros e monitorar logs de comunicação.",
                "kind": "config",
            },
            {
                "title": "Tools / MCP / Integrações",
                "href": "/integrations",
                "description": "Gerenciar provedores, segredos operacionais e conectividade do ecossistema.",
                "kind": "config",
            },
            {
                "title": "Auditoria Operacional",
                "href": "/operations/audit",
                "description": "Conferir trilhas MCP, Sapiens, intervenções humanas e evidências operacionais.",
                "kind": "audit",
            },
        ]

        registration_links = [
            {
                "title": "Usuários do sistema",
                "href": "/auth/users/page",
                "description": "Consultar e revisar usuários aptos a operar as surfaces privilegiadas.",
                "kind": "cadastro",
            },
            {
                "title": "Meu perfil",
                "href": "/auth/profile",
                "description": "Ajustar identidade, contatos e contexto pessoal do operador.",
                "kind": "cadastro",
            },
            {
                "title": "Cadastros-base financeiros",
                "href": "/financial/catalogs",
                "description": "Manter contas, centros de resultado, favorecidos e estruturas que influenciam a IA.",
                "kind": "cadastro",
            },
            {
                "title": "Domínios habilitados",
                "href": "/financial/domain-enablements",
                "description": "Controlar projetos e processos que podem ser cruzados nas automações e análises.",
                "kind": "cadastro",
            },
        ]

        operational_links = [
            {
                "title": "Sapiens",
                "href": "/sapiens",
                "description": "Acesso direto ao runtime conversacional oficial do APP32.",
            },
            {
                "title": "Mapa de integrações",
                "href": "/integrations",
                "description": "Conferir provedores externos, canais e políticas de segredo.",
            },
            {
                "title": "Route audit",
                "href": "/route-audit/",
                "description": "Auditar logging, cobertura e pontos expostos da plataforma.",
            },
        ]

        return {
            "active_company": {
                "id": getattr(active_company, "id", None),
                "name": getattr(active_company, "name", None),
                "client_code": getattr(active_company, "client_code", None),
            },
            "summary": {
                "profiles": len(profiles),
                "surfaces": len(surfaces),
                "domains": len(domains),
                "permission_matrices": len(permissions),
                "catalog_tools": len(capability_tools),
                "human_gate_tools": sum(1 for tool in capability_tools if tool.get("human_gate")),
                "critical_tools": risk_counter.get("critical", 0),
                "release_checks": len(release["checklist"]),
                "release_smokes": len(release["smokes"]),
                "freeze_triggers": len(freeze["triggers"]),
                "onboarding_steps": len(onboarding["steps"]),
                "readiness_gates": len(readiness["gates"]),
                "dashboard_panels": len(dashboard["panels"]),
            },
            "profiles": profiles,
            "surfaces": surfaces,
            "domains": domains,
            "permissions": permissions,
            "catalog": {
                "manifest_version": capability_manifest.get("version"),
                "tools": capability_tools,
                "domain_distribution": [
                    {"domain": domain, "count": count}
                    for domain, count in sorted(domain_counter.items(), key=lambda item: (-item[1], item[0]))
                ],
                "risk_distribution": [
                    {"risk": risk, "count": count}
                    for risk, count in sorted(risk_counter.items(), key=lambda item: item[0])
                ],
                "surfaces": surface_capabilities,
            },
            "onboarding": onboarding,
            "release": release,
            "freeze": freeze,
            "dashboard": dashboard,
            "readiness": readiness,
            "readiness_by_phase": readiness_by_phase,
            "configuration_links": configuration_links,
            "registration_links": registration_links,
            "operational_links": operational_links,
        }
