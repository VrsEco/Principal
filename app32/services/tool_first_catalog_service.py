from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from src.intelligence.tool_catalog import catalog


class ToolFirstCatalogService:
    """Publica um catálogo orientado a domínio para convergência Sapiens + MCP."""

    DOMAIN_SPECS = (
        {
            "key": "company_onboarding",
            "title": "Onboarding de Empresa",
            "status": "canonical",
            "description": "Fluxo assistido para criação de tenant/empresa com bootstrap administrativo.",
            "legacy_routes": ["/agents/cadastro"],
            "canonical_routes": ["/companies/new"],
            "entrypoint": "/companies/new",
            "surface": "onboarding",
            "rest_contracts": [
                {
                    "name": "start_company_onboarding",
                    "method": "POST",
                    "path": "/api/cadastro-agent/empresa/iniciar",
                    "status": "ready",
                },
                {
                    "name": "process_company_onboarding_step",
                    "method": "POST",
                    "path": "/api/cadastro-agent/empresa/processar",
                    "status": "ready",
                },
                {
                    "name": "finalize_company_onboarding",
                    "method": "POST",
                    "path": "/api/cadastro-agent/empresa/finalizar",
                    "status": "ready",
                },
            ],
            "mcp_contracts": [
                {
                    "name": "list_app32_capabilities",
                    "status": "ready",
                    "notes": "Discovery oficial do catálogo compartilhado Sapiens/MCP.",
                },
                {
                    "name": "create_company",
                    "status": "planned",
                    "notes": "Contrato MCP dedicado do onboarding ainda não foi exposto; hoje o fluxo canônico está no service + REST.",
                },
            ],
            "tool_names": (),
            "planned_tools": ("create_company", "analyze_company_completeness", "continue_company_onboarding"),
            "governance": [
                "Multi-tenancy obrigatório na criação da company e vínculo do usuário.",
                "Bootstrap administrativo com Role Administrador + Employee do usuário logado.",
            ],
        },
        {
            "key": "strategy",
            "title": "Planejamento Estratégico",
            "status": "wrapper",
            "description": "Domínio convergido para o Sapiens com especialização por tools e prompts guiados.",
            "legacy_routes": ["/agents/planejamento"],
            "canonical_routes": ["/sapiens"],
            "entrypoint": "/sapiens?contact=sapiens&surface=planejamento",
            "surface": "sapiens",
            "rest_contracts": [
                {
                    "name": "open_strategy_wrapper",
                    "method": "GET",
                    "path": "/agents/planejamento",
                    "status": "ready",
                },
                {
                    "name": "chat_with_sapiens",
                    "method": "POST",
                    "path": "/api/agents/chat",
                    "status": "ready",
                },
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery por domínio/escopo."},
            ],
            "tool_names": ("list_plans", "get_plan_diagnostics", "get_plan_diagnostics_read_model", "update_plan_section"),
            "planned_tools": ("generate_strategy_snapshot", "suggest_okrs", "list_strategic_gaps"),
            "governance": [
                "Ferramentas estratégicas devem priorizar leitura analítica antes de mutações.",
                "Ações sensíveis continuam sujeitas a RBAC e human gate quando aplicável.",
            ],
        },
        {
            "key": "processes",
            "title": "Processos",
            "status": "wrapper",
            "description": "Processos operacionais e mapa funcional agora orbitam o hub Sapiens.",
            "legacy_routes": ["/agents/processos"],
            "canonical_routes": ["/sapiens"],
            "entrypoint": "/sapiens?contact=sapiens&surface=processos",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_process_wrapper", "method": "GET", "path": "/agents/processos", "status": "ready"},
                {"name": "chat_with_sapiens", "method": "POST", "path": "/api/agents/chat", "status": "ready"},
                {"name": "workflow_catalog", "method": "GET", "path": "/api/agents/workflows/catalog", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery por domínio/escopo."},
            ],
            "tool_names": ("create_process_area", "create_macro_process", "create_process", "list_process_hierarchy"),
            "planned_tools": ("list_processes", "map_process", "analyze_process_bottlenecks"),
            "governance": [
                "Criação de processo com impacto operacional deve manter human gate.",
                "Catálogo de workflow é a base para descoberta antes de novos fluxos.",
            ],
        },
        {
            "key": "routine",
            "title": "Rotina Operacional",
            "status": "wrapper",
            "description": "Rotina, follow-up e acompanhamento do dia a dia passam a ser guiados pelo Sapiens.",
            "legacy_routes": ["/agents/rotina"],
            "canonical_routes": ["/sapiens", "/my-work"],
            "entrypoint": "/sapiens?contact=sapiens&surface=rotina",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_routine_wrapper", "method": "GET", "path": "/agents/rotina", "status": "ready"},
                {"name": "chat_with_sapiens", "method": "POST", "path": "/api/agents/chat", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery por domínio/escopo."},
            ],
            "tool_names": ("get_my_work",),
            "planned_tools": ("list_pending_tasks", "summarize_team_workload", "generate_followup_actions"),
            "governance": [
                "O domínio deve operar no contexto da empresa ativa do usuário.",
                "Priorizar leitura e recomendação antes de automações de cobrança/execução.",
            ],
        },
        {
            "key": "performance",
            "title": "Performance",
            "status": "wrapper",
            "description": "Leitura de indicadores, tendência e risco operacional centralizada no Sapiens.",
            "legacy_routes": ["/agents/performance"],
            "canonical_routes": ["/sapiens", "/configs/ai/mcp"],
            "entrypoint": "/sapiens?contact=sapiens&surface=performance",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_performance_wrapper", "method": "GET", "path": "/agents/performance", "status": "ready"},
                {"name": "chat_with_sapiens", "method": "POST", "path": "/api/agents/chat", "status": "ready"},
                {"name": "open_mcp_console", "method": "GET", "path": "/configs/ai/mcp", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery por domínio/escopo."},
            ],
            "tool_names": (),
            "planned_tools": ("list_indicators", "analyze_indicator_trends", "detect_performance_risk"),
            "governance": [
                "Leituras analíticas devem preservar tenant scope e evidências de origem.",
                "Indicadores sensíveis precisam de trilha de auditoria quando cruzarem múltiplos domínios.",
            ],
        },
        {
            "key": "executive",
            "title": "Leitura Estratégica Executiva",
            "status": "wrapper",
            "description": "Resumo executivo e leitura de coerência estratégia x execução via hub Sapiens.",
            "legacy_routes": ["/agents/estrategico"],
            "canonical_routes": ["/sapiens", "/configs/ai/mcp"],
            "entrypoint": "/sapiens?contact=sapiens&surface=estrategico",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_executive_wrapper", "method": "GET", "path": "/agents/estrategico", "status": "ready"},
                {"name": "chat_with_sapiens", "method": "POST", "path": "/api/agents/chat", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery por domínio/escopo."},
            ],
            "tool_names": (),
            "planned_tools": ("generate_executive_summary", "compare_strategy_vs_execution", "list_strategic_risks"),
            "governance": [
                "Leitura executiva deve consolidar evidências antes de recomendar ação sensível.",
                "Domínio permanece wrapper até a publicação de tools específicas.",
            ],
        },
        {
            "key": "engineering",
            "title": "Squad de Engenharia",
            "status": "canonical",
            "description": "Canal técnico para diagnóstico, evolução, auditoria e convergência arquitetural do APP32.",
            "legacy_routes": ["/agents/engineering"],
            "canonical_routes": ["/sapiens?contact=engineering", "/configs/ai/mcp"],
            "entrypoint": "/sapiens?contact=engineering",
            "surface": "engineering",
            "rest_contracts": [
                {"name": "open_engineering_channel", "method": "GET", "path": "/agents/engineering", "status": "ready"},
                {"name": "chat_with_engineering", "method": "POST", "path": "/api/agents/chat", "status": "ready"},
                {"name": "open_mcp_console", "method": "GET", "path": "/configs/ai/mcp", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery central de capacidades e segurança."},
            ],
            "tool_names": ("consult_rules", "escalate_technical_issue", "query_database"),
            "planned_tools": ("run_operational_audit", "publish_tool_contract", "review_route_surface"),
            "governance": [
                "Uso técnico deve privilegiar MCP First e trilha de auditoria em produção.",
                "Consultas livres e operações de risco alto devem manter human gate.",
            ],
        },
    )

    @staticmethod
    def _normalize_filter_values(value: str | Iterable[str] | None) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            raw_values = value.split(",")
        else:
            raw_values = value
        return {str(item).strip().lower() for item in raw_values if str(item).strip()}

    @classmethod
    def build_catalog(
        cls,
        active_company: Any | None = None,
        *,
        domain: str | Iterable[str] | None = None,
        status: str | Iterable[str] | None = None,
        surface: str | Iterable[str] | None = None,
        include_backlog: bool = True,
    ) -> dict[str, Any]:
        manifest = catalog.get_capability_manifest(include_tools=True)
        tools = list(manifest.get("tools", []))
        tools_by_name = {str(tool.get("name")): tool for tool in tools if tool.get("name")}
        domain_filter = cls._normalize_filter_values(domain)
        status_filter = cls._normalize_filter_values(status)
        surface_filter = cls._normalize_filter_values(surface)

        domains = []
        status_counter: Counter[str] = Counter()
        total_ready_rest = 0
        total_ready_mcp = 0

        for spec in cls.DOMAIN_SPECS:
            spec_key = str(spec["key"]).strip().lower()
            spec_surface = str(spec["surface"]).strip().lower()
            spec_status = str(spec["status"]).strip().lower()
            if domain_filter and spec_key not in domain_filter:
                continue
            if status_filter and spec_status not in status_filter:
                continue
            if surface_filter and spec_surface not in surface_filter:
                continue

            published_tools = [tools_by_name[name] for name in spec["tool_names"] if name in tools_by_name]
            published_names = {tool["name"] for tool in published_tools}
            backlog_tools = [
                {
                    "name": name,
                    "status": "planned",
                }
                for name in spec["planned_tools"]
                if name not in published_names
            ]
            if not include_backlog:
                backlog_tools = []

            ready_rest = sum(1 for item in spec["rest_contracts"] if item["status"] == "ready")
            ready_mcp = sum(1 for item in spec["mcp_contracts"] if item["status"] == "ready") + len(published_tools)
            total_ready_rest += ready_rest
            total_ready_mcp += ready_mcp
            status_counter.update([spec["status"]])

            domains.append(
                {
                    "key": spec["key"],
                    "title": spec["title"],
                    "status": spec["status"],
                    "description": spec["description"],
                    "surface": spec["surface"],
                    "legacy_routes": list(spec["legacy_routes"]),
                    "canonical_routes": list(spec["canonical_routes"]),
                    "entrypoint": spec["entrypoint"],
                    "rest_contracts": list(spec["rest_contracts"]),
                    "mcp_contracts": list(spec["mcp_contracts"]),
                    "published_tools": published_tools,
                    "planned_tools": backlog_tools,
                    "summary": {
                        "ready_rest_contracts": ready_rest,
                        "published_mcp_tools": len(published_tools),
                        "ready_mcp_entries": ready_mcp,
                    },
                    "governance": list(spec["governance"]),
                }
            )

        return {
            "version": "2026-04-11",
            "active_company": {
                "id": getattr(active_company, "id", None),
                "name": getattr(active_company, "name", None),
                "client_code": getattr(active_company, "client_code", None),
            },
            "summary": {
                "domains": len(domains),
                "canonical_domains": status_counter.get("canonical", 0),
                "wrapper_domains": status_counter.get("wrapper", 0),
                "ready_rest_contracts": total_ready_rest,
                "ready_mcp_entries": total_ready_mcp,
            },
            "filters": {
                "domain": sorted(domain_filter),
                "status": sorted(status_filter),
                "surface": sorted(surface_filter),
                "include_backlog": include_backlog,
            },
            "domains": domains,
            "discovery": {
                "rest_endpoint": "/api/configs/ai/mcp/tool-first-catalog",
                "frontend_state_endpoint": "/api/configs/ai/mcp/frontend-state",
                "mcp_tool": "list_app32_capabilities",
                "console_url": "/configs/ai/mcp",
            },
            "principles": [
                "Sapiens e Squad de Engenharia são as interfaces centrais do APP32.",
                "Especialização por domínio deve nascer em service + REST + MCP Tool.",
                "Superfícies /agents legadas passam a atuar como wrappers temporários ou onboarding canônico.",
            ],
        }
