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
            "tool_names": ("create_process_area", "create_macro_process", "update_macro_process", "create_process", "list_process_hierarchy"),
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
            "key": "commercial_contracts",
            "title": "Gestão Comercial",
            "status": "canonical",
            "description": "Clientes, carteiras, contratos, catálogo comercial, faturamento nativo e esteira fiscal/NFS-e.",
            "legacy_routes": [],
            "canonical_routes": [
                "/contracts",
                "/contracts/list",
                "/contracts/customers/portfolio",
                "/contracts/customers",
                "/contracts/catalogs/items",
                "/contracts/legal-entities",
                "/contracts/billing",
                "/contracts/billing/review",
                "/contracts/billing/done",
                "/contracts/invoices",
            ],
            "entrypoint": "/contracts",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_contracts_workspace", "method": "GET", "path": "/contracts", "status": "ready"},
                {"name": "open_contracts_list", "method": "GET", "path": "/contracts/list", "status": "ready"},
                {"name": "open_commercial_customers", "method": "GET", "path": "/contracts/customers", "status": "ready"},
                {"name": "open_commercial_billing", "method": "GET", "path": "/contracts/billing", "status": "ready"},
                {"name": "open_commercial_fiscal_invoices", "method": "GET", "path": "/contracts/invoices", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery por domínio governance/finance e tags commercial."},
                {"name": "describe_app32_crud_contracts_tool", "status": "ready", "notes": "Contrato CRUD inclui Governança Comercial/Contratos."},
            ],
            "tool_names": (
                "get_commercial_dashboard",
                "list_commercial_customer_portfolios",
                "create_commercial_customer_portfolio",
                "update_commercial_customer_portfolio",
                "toggle_commercial_customer_portfolio",
                "list_commercial_customers",
                "update_commercial_customer",
                "list_commercial_issuers",
                "create_commercial_issuer",
                "update_commercial_issuer",
                "list_commercial_catalog_structure",
                "create_commercial_catalog_structure_item",
                "update_commercial_catalog_structure_item",
                "toggle_commercial_catalog_structure_item",
                "list_commercial_products_services",
                "create_commercial_product_service",
                "update_commercial_product_service",
                "toggle_commercial_product_service",
                "list_commercial_contracts",
                "get_commercial_contract_workspace",
                "create_commercial_contract",
                "update_commercial_contract_general",
                "suspend_commercial_contract",
                "close_commercial_contract",
                "delete_commercial_contract",
                "add_commercial_contract_item",
                "update_commercial_contract_item",
                "upsert_commercial_contract_financial_terms",
                "upsert_commercial_contract_fiscal_terms",
                "list_commercial_billing_queue",
                "build_commercial_billing_review",
                "preview_commercial_billing_batch",
                "generate_commercial_billing_batch",
                "list_commercial_billings_done",
                "generate_commercial_financial_titles_for_billing",
                "cancel_commercial_billing",
                "list_commercial_fiscal_workspace",
                "update_commercial_fiscal_entry",
                "assign_commercial_fiscal_batch",
                "remove_commercial_fiscal_batch",
                "update_commercial_fiscal_status",
                "export_commercial_fiscal_integration_spreadsheet",
            ),
            "planned_tools": (
                "upload_commercial_fiscal_invoice_files",
                "list_commercial_opportunities",
                "create_commercial_opportunity",
                "list_commercial_proposals",
            ),
            "governance": [
                "Capabilities comerciais usam domínios canônicos governance e finance até eventual SPEC de domínio commercial dedicado.",
                "Toda operação exige company_id; faturamento, cancelamento e geração de títulos mantêm trilha auditável e human gate.",
                "Mutações fiscais/financeiras seguem menor privilégio e não devem ser publicadas em analytics.",
            ],
        },
        {
            "key": "finance",
            "title": "Gestão Financeira",
            "status": "canonical",
            "description": "Cadastros, títulos, orçamento, conciliação, classificação, borderôs, relatórios e automações financeiras.",
            "legacy_routes": [],
            "canonical_routes": ["/financial", "/financial/catalogs", "/financial/schedules", "/financial/budget", "/financial/reconciliation"],
            "entrypoint": "/financial",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_financial_workspace", "method": "GET", "path": "/financial", "status": "ready"},
                {"name": "open_financial_schedules", "method": "GET", "path": "/financial/schedules", "status": "ready"},
                {"name": "open_financial_budget", "method": "GET", "path": "/financial/budget", "status": "ready"},
                {"name": "open_financial_reconciliation", "method": "GET", "path": "/financial/reconciliation", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery do domínio finance nas surfaces user/admin/analytics conforme policy."},
            ],
            "tool_names": (
                "list_financial_catalog_items",
                "create_financial_catalog_item",
                "update_financial_catalog_item",
                "toggle_financial_catalog_item",
                "list_financial_schedules",
                "create_financial_schedule",
                "update_financial_schedule",
                "toggle_financial_schedule",
                "generate_due_financial_schedules",
                "list_financial_borderos",
                "get_financial_bordero",
                "create_financial_bordero",
                "create_financial_bordero_settlement",
                "list_financial_entries",
                "get_financial_entry",
                "create_financial_entry",
                "create_financial_direct_entry",
                "replace_financial_allocations",
                "create_financial_settlement",
                "list_financial_import_batches",
                "process_financial_import_batch",
                "reconcile_financial_import_batch",
                "get_financial_bank_reconciliation_workspace",
                "list_financial_classification_rules",
                "classify_financial_import_batch",
                "get_financial_classification_dashboard",
                "list_financial_closings",
                "create_financial_closing",
                "list_financial_report_types",
                "generate_financial_report",
                "get_financial_executive_dashboard",
                "list_financial_budget_versions",
                "create_financial_budget_version",
                "get_financial_budget_matrix",
                "upsert_financial_budget_matrix",
                "get_incentive_indicators",
            ),
            "planned_tools": ("forecast_financial_cashflow", "detect_financial_anomalies", "approve_financial_closing"),
            "governance": [
                "Domínio finance é sensível: analytics é somente leitura/análise e mutações exigem permissões equivalentes à web.",
                "Deletes/execuções de alto impacto devem permanecer em admin com confirmação explícita.",
            ],
        },
        {
            "key": "work_journey",
            "title": "Jornada Operacional",
            "status": "canonical",
            "description": "Blocos, regras, agenda, tarefas, calendário, capacidade, ausências e transferências da rotina operacional.",
            "legacy_routes": [],
            "canonical_routes": ["/my-work", "/process-routines/analysis", "/efficiency-analysis"],
            "entrypoint": "/my-work",
            "surface": "sapiens",
            "rest_contracts": [
                {"name": "open_my_work", "method": "GET", "path": "/my-work", "status": "ready"},
                {"name": "open_process_routines_analysis", "method": "GET", "path": "/process-routines/analysis", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Discovery do domínio routine com tags work_journey."},
            ],
            "tool_names": (
                "get_work_journey_board_tool",
                "list_work_journey_blocks_tool",
                "save_work_journey_block_tool",
                "delete_work_journey_block_tool",
                "list_work_journey_rules_tool",
                "save_work_journey_rule_tool",
                "delete_work_journey_rule_tool",
                "update_work_journey_item_tool",
                "list_work_journey_manual_tasks_tool",
                "create_work_journey_manual_task_tool",
                "delete_work_journey_manual_task_tool",
                "get_work_journey_agenda_tool",
                "move_work_journey_agenda_item_tool",
                "generate_work_journey_agenda_tool",
                "lock_work_journey_agenda_tool",
                "unlock_work_journey_agenda_tool",
                "list_routine_journey_bindings_tool",
                "save_routine_journey_binding_tool",
                "list_employee_process_routines_for_journey_tool",
                "list_work_calendar_events_tool",
                "create_work_calendar_event_tool",
                "update_work_calendar_event_tool",
                "delete_work_calendar_event_tool",
                "list_work_journey_task_inventory_tool",
                "get_work_journey_capacity_report_tool",
                "get_process_routines_analysis_tool",
                "get_efficiency_collaborators_analysis_tool",
                "list_work_journey_absences_tool",
                "create_work_journey_absence_request_tool",
                "approve_work_journey_absence_request_tool",
                "list_work_journey_transfers_tool",
                "create_work_journey_transfer_request_tool",
                "approve_work_journey_transfer_request_tool",
            ),
            "planned_tools": ("suggest_work_journey_rebalancing", "detect_work_journey_overload"),
            "governance": [
                "Rotina usa domínio canônico routine; work/tasks/worklog permanecem aliases, não novos domínios.",
                "Aprovações e exclusões de jornada exigem confirmação e trilha auditável.",
            ],
        },
        {
            "key": "mcp_governance",
            "title": "Governança MCP e Instruction Registry",
            "status": "canonical",
            "description": "Catálogos, contratos, surfaces, readiness, release, usage, Sapiens Factory, sessão de empresa e integrações.",
            "legacy_routes": [],
            "canonical_routes": ["/configs/ai/mcp", "/ai-tools", "/ai-capability-inventory"],
            "entrypoint": "/configs/ai/mcp",
            "surface": "engineering",
            "rest_contracts": [
                {"name": "open_mcp_console", "method": "GET", "path": "/configs/ai/mcp", "status": "ready"},
                {"name": "open_ai_tools_catalog", "method": "GET", "path": "/ai-tools", "status": "ready"},
                {"name": "open_ai_capability_inventory", "method": "GET", "path": "/ai-capability-inventory", "status": "ready"},
            ],
            "mcp_contracts": [
                {"name": "list_app32_capabilities", "status": "ready", "notes": "Manifesto central de capabilities."},
                {"name": "list_feature_catalog", "status": "ready", "notes": "Catálogo documental MCP com bootstrap por surface."},
            ],
            "tool_names": (
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
                "describe_app32_instruction_registry_tool",
                "resolve_app32_instruction_bundle_tool",
                "describe_app32_operational_readiness_tool",
                "describe_app32_permission_matrix_tool",
                "describe_app32_profile_contracts_tool",
                "describe_app32_release_checklist_tool",
                "describe_app32_sapiens_factory_tool",
                "assess_app32_change_request_tool",
                "trace_app32_capability_dependencies_tool",
                "describe_app32_available_sapiens_squads_tool",
                "resolve_app32_sapiens_activation_tool",
                "describe_app32_session_company_scope_tool",
                "select_app32_session_company_tool",
                "clear_app32_session_company_tool",
                "describe_app32_squad_runtime_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_tool_freeze_procedure_tool",
                "describe_app32_usage_dashboard_tool",
                "list_app32_integrations_catalog",
                "request_new_app32_integration",
            ),
            "planned_tools": ("publish_mcp_capability_contract", "diff_mcp_surface_manifests"),
            "governance": [
                "Catálogo MCP remoto e stdio devem reaproveitar o mesmo registry de surfaces.",
                "Toda mudança em profiles, permission matrix, playbooks e capabilities deve evitar drift documental e de policy.",
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
            "tool_names": (
                "consult_rules",
                "escalate_technical_issue",
                "request_engineering_suggestion",
                "list_my_engineering_suggestions",
                "query_database",
            ),
            "planned_tools": ("run_operational_audit", "publish_tool_contract", "review_route_surface"),
            "governance": [
                "Uso técnico deve privilegiar MCP First e trilha de auditoria em produção.",
                "Consultas livres e operações de risco alto devem manter human gate.",
                "Sugestões funcionais e melhorias devem gerar card formal em AA.J.1 via request_engineering_suggestion.",
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
            "version": "2026-06-06",
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
