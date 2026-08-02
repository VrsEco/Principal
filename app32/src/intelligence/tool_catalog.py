"""
Catálogo único de tools do APP32 para Sapiens e MCP.

Diretriz:
- Sapiens e MCP devem partir do mesmo ponto de verdade para o catálogo.
- Tools LangChain existentes seguem disponíveis para ambos.
- Registradores MCP adicionais podem complementar o catálogo sem duplicar o core.
"""

from __future__ import annotations

import logging
from functools import wraps
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable, Iterable, List, Sequence

from src.intelligence.audit import build_ai_execution_audit_record, emit_ai_execution_audit_event
from src.core.mcp_http_auth import get_http_request_context, get_http_request_identity
from src.intelligence.knowledge_tools import knowledge_langchain_tools
from src.intelligence.tools import tools as legacy_langchain_tools
from src.core.mcp_analysis_catalog_tools import register_analysis_catalog_tools
from src.core.mcp_commercial_tools import register_commercial_mcp_tools
from src.core.mcp_consultive_assisted_analysis_tools import register_consultive_assisted_analysis_tools
from src.core.mcp_runtime import wrap_mcp_callable
from src.core.mcp_crud_contract_tools import register_crud_contract_tools
from src.core.mcp_domain_example_tools import register_domain_example_tools
from src.core.mcp_domain_playbook_tools import register_domain_playbook_tools
from src.core.mcp_external_ai_onboarding_tools import register_external_ai_onboarding_tools
from src.core.mcp_external_llm_factory_tools import register_external_llm_factory_tools
from src.core.mcp_financial_tools import register_financial_mcp_tools
from src.core.mcp_incentive_tools import register_incentive_tools
from src.core.mcp_integration_request_tools import register_integration_request_tools
from src.core.mcp_instruction_registry_tools import register_instruction_registry_tools
from src.core.mcp_knowledge_tools import register_knowledge_tools
from src.core.mcp_strategic_tree_tools import register_strategic_tree_tools
from src.core.mcp_operational_readiness_tools import register_operational_readiness_tools
from src.core.mcp_operation_router_tools import register_operation_router_tools
from src.core.mcp_permission_matrix_tools import register_permission_matrix_tools
from src.core.mcp_plan_driver_tools import register_plan_driver_tools
from src.core.mcp_plan_global_okr_tools import register_plan_global_okr_tools
from src.core.mcp_plan_global_okr_correction_tools import register_plan_global_okr_correction_tools
from src.core.mcp_plan_participant_tools import register_plan_participant_tools
from src.core.mcp_process_flow_tools import register_process_flow_tools
from src.core.mcp_process_improvement_tools import register_process_improvement_tools
from src.core.mcp_process_pop_tools import register_process_pop_tools
from src.core.mcp_profile_contract_tools import register_profile_contract_tools
from src.core.mcp_real_estate_auction_tools import register_real_estate_auction_tools
from src.core.mcp_release_checklist_tools import register_release_checklist_tools
from src.core.mcp_sector_strategy_tools import register_sector_strategy_tools
from src.core.mcp_sapiens_activation_tools import register_sapiens_activation_tools
from src.core.mcp_sapiens_factory_tools import register_sapiens_factory_tools
from src.core.mcp_session_company_tools import register_session_company_tools
from src.core.mcp_session_harness_tools import register_session_harness_tools
from src.core.mcp_squad_runtime_tools import register_squad_runtime_tools
from src.core.mcp_strategy_alignment_tools import register_strategy_alignment_tools
from src.core.mcp_surface_playbook_tools import register_surface_playbook_tools
from src.core.mcp_tool_freeze_tools import register_tool_freeze_tools
from src.core.mcp_usage_dashboard_tools import register_usage_dashboard_tools
from src.core.mcp_work_journey_analytics_tools import register_work_journey_analytics_tools
from src.core.mcp_work_journey_tools import register_work_journey_tools
from src.intelligence.tooling.registry import ToolCapabilityRegistry
from src.intelligence.tooling.capabilities import ToolScope

try:
    from src.core.mcp_feature_catalog_tools import register_feature_catalog_tools
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com deploy parcial
    register_feature_catalog_tools = None

try:
    from src.core.mcp_implantation_persona_profile_tools import register_implantation_persona_profile_tools
except ModuleNotFoundError:  # pragma: no cover - compatibilidade com deploy parcial
    register_implantation_persona_profile_tools = None


McpRegistrar = Callable[[object], None]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCatalog:
    langchain_tools: Sequence[object]
    mcp_registrars: Sequence[McpRegistrar]
    capability_registry: ToolCapabilityRegistry = field(default_factory=lambda: ToolCapabilityRegistry(capabilities={}))

    def get_langchain_tools(self) -> List[object]:
        return list(self.langchain_tools)

    def iter_langchain_tools(self) -> Iterable[object]:
        return iter(self.langchain_tools)

    def get_tool_capability(self, tool_name: str):
        return self.capability_registry.get(tool_name)

    def iter_capabilities(self, scope: str | ToolScope | Sequence[str | ToolScope] | None = None, domain: str | Sequence[str] | None = None):
        return self.capability_registry.iter(scope=scope, domain=domain)

    def get_capability_manifest(
        self,
        *,
        scope: str | ToolScope | Sequence[str | ToolScope] | None = None,
        domain: str | Sequence[str] | None = None,
        include_tools: bool = True,
    ) -> dict:
        return self.capability_registry.to_manifest(scope=scope, domain=domain, include_tools=include_tools)

    def register_mcp_tools(self, mcp: object) -> None:
        """
        Registra todas as tools compartilhadas no servidor MCP.
        """
        def _extract_context(raw: object) -> dict[str, object]:
            payload: dict[str, object] = {}
            if isinstance(raw, dict):
                payload = dict(raw)
            elif isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], dict):
                payload = dict(raw[0])

            http_context = dict(get_http_request_context() or {})
            http_identity = get_http_request_identity()

            context: dict[str, object] = dict(http_context)
            if http_identity is not None:
                context.setdefault("client_id", getattr(http_identity, "client_id", None))
                context.setdefault("user_id", getattr(http_identity, "user_id", None))
                context.setdefault("company_id", getattr(http_identity, "company_id", None))
                context.setdefault("fallback_role", getattr(http_identity, "fallback_role", None))
            for key in (
                "company_id",
                "user_id",
                "thread_id",
                "request_id",
                "trace_id",
                "fallback_role",
                "surface",
                "transport",
                "client",
                "runtime_profile",
                "actor_type",
                "client_id",
                "token_subject",
            ):
                if payload.get(key) is not None:
                    context[key] = payload.get(key)
            return context

        def _safe_int(value: object) -> int | None:
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip().isdigit():
                return int(value.strip())
            return None

        def _audit_mcp_tool(
            *,
            tool_name: str,
            status: str,
            payload: dict[str, object] | None = None,
            error: Exception | None = None,
            domain: str | None = None,
        ) -> None:
            capability = self.get_tool_capability(tool_name)
            metadata = {
                "risk": getattr(capability, "risk", None).value if getattr(capability, "risk", None) else None,
                "error_type": error.__class__.__name__ if error else None,
                "error_message": str(error) if error else None,
                "actor_role": str((payload or {}).get("fallback_role") or "").strip().lower() or None,
                "surface": str((payload or {}).get("surface") or "").strip().lower() or None,
                "transport": str((payload or {}).get("transport") or "").strip().lower() or None,
                "client": str((payload or {}).get("client") or "").strip().lower() or None,
                "runtime_profile": str((payload or {}).get("runtime_profile") or "").strip().lower() or None,
                "actor_type": str((payload or {}).get("actor_type") or "").strip().lower() or None,
                "client_id": str((payload or {}).get("client_id") or "").strip() or None,
                "token_subject": str((payload or {}).get("token_subject") or "").strip() or None,
            }
            record = build_ai_execution_audit_record(
                event_type=f"mcp.{tool_name}.{status}",
                runtime="mcp",
                status=status,
                domain=domain or getattr(capability, "domain", None),
                operation=tool_name,
                tool_name=tool_name,
                scope="mcp",
                company_id=_safe_int((payload or {}).get("company_id")),
                user_id=_safe_int((payload or {}).get("user_id")),
                thread_id=str((payload or {}).get("thread_id")) if (payload or {}).get("thread_id") else None,
                request_id=str((payload or {}).get("request_id")) if (payload or {}).get("request_id") else None,
                trace_id=str((payload or {}).get("trace_id")) if (payload or {}).get("trace_id") else None,
                metadata={key: value for key, value in metadata.items() if value is not None},
            )
            emit_ai_execution_audit_event(record, logger=logger)

        for tool in self.langchain_tools:
            if hasattr(tool, "func"):
                original_func = tool.func

                @mcp.tool(name=tool.name, description=tool.description)
                @wraps(original_func)
                @wrap_mcp_callable
                def _wrapped_tool(*args, __current_tool=tool, **kwargs):
                    payload = _extract_context(kwargs if kwargs else (args[0] if args else {}))
                    _audit_mcp_tool(tool_name=__current_tool.name, status="start", payload=payload)
                    try:
                        result = original_func(*args, **kwargs)
                        _audit_mcp_tool(tool_name=__current_tool.name, status="success", payload=payload)
                        return result
                    except Exception as exc:
                        _audit_mcp_tool(tool_name=__current_tool.name, status="failure", payload=payload, error=exc)
                        raise
            else:
                def make_wrapper(current_tool):
                    original_invoke = current_tool.invoke

                    @mcp.tool(name=current_tool.name, description=current_tool.description)
                    @wraps(original_invoke)
                    @wrap_mcp_callable
                    def mcp_tool_wrapper(*args, **kwargs):
                        payload = _extract_context(kwargs if kwargs else (args[0] if args else {}))
                        _audit_mcp_tool(tool_name=current_tool.name, status="start", payload=payload)
                        try:
                            result = original_invoke(kwargs if kwargs else args[0] if args else {})
                            _audit_mcp_tool(tool_name=current_tool.name, status="success", payload=payload)
                            return result
                        except Exception as exc:
                            _audit_mcp_tool(tool_name=current_tool.name, status="failure", payload=payload, error=exc)
                            raise
                    return mcp_tool_wrapper

                make_wrapper(tool)

        for registrar in self.mcp_registrars:
            registrar(mcp)

        @mcp.tool(
            name="list_app32_capabilities",
            description="Lista as capacidades e metadados de segurança do catálogo MCP/Sapiens do APP32.",
        )
        def list_app32_capabilities(
            scope: str | None = None,
            domain: str | None = None,
            include_tools: bool = True,
        ) -> dict:
            """Manifesto consultável por agentes para descoberta de capacidades."""

            scope_filter: str | ToolScope | Sequence[str | ToolScope] | None = scope
            domain_filter: str | Sequence[str] | None = domain
            manifest = self.get_capability_manifest(
                scope=scope_filter,
                domain=domain_filter,
                include_tools=include_tools,
            )
            _audit_mcp_tool(
                tool_name="list_app32_capabilities",
                status="success",
                payload={
                    "scope": scope or "",
                    "domain": domain or "",
                },
                domain="governance",
            )
            return manifest


_supplemental_mcp_tools = (
    SimpleNamespace(name="strategic_tree_list", description="Lista Árvores Estratégicas autorizadas do tenant."),
    SimpleNamespace(name="strategic_tree_get", description="Obtém a estrutura de uma Árvore Estratégica do tenant."),
    SimpleNamespace(name="strategic_tree_get_branch", description="Lê ramo e contribuições autorizadas de uma Árvore Estratégica."),
    SimpleNamespace(name="strategic_tree_add_contribution", description="Registra contribuição humana confirmada na Árvore Estratégica, sem escrita canônica."),
    SimpleNamespace(
        name="correct_plan_global_okrs_tool",
        description="Corrige os dois OKRs Globais do plano e refaz seus vínculos setoriais com confirmação humana.",
    ),
    SimpleNamespace(
        name="create_and_link_plan_global_okrs_tool",
        description="Cria dois OKRs Globais e os vincula aos respectivos OKRs de Área do planejamento.",
    ),
    SimpleNamespace(
        name="create_single_plan_driver_tool",
        description="Cadastra de forma idempotente o único direcionador confirmado de um planejamento growth.",
    ),
    SimpleNamespace(
        name="sync_plan_participants_tool",
        description="Sincroniza todos os colaboradores ativos do tenant como participantes do plano e define um owner oficial.",
    ),
    SimpleNamespace(
        name="create_sector_okr_structure_tool",
        description="Cadastra atomicamente OKRs setoriais, resultados-chave propostos e iniciativas vinculadas, com confirmação humana.",
    ),
    SimpleNamespace(name="create_process_bpmn_activity_tool", description="Cria uma atividade BPMN, conexões e Data Object Reference no diagrama draft."),
    SimpleNamespace(
        name="analyze_process_flow_copilot_tool",
        description="Analisa o fluxo BPMN do processo e aponta gaps de lane, POP, gateways e oportunidades de automação/conexão.",
    ),
    SimpleNamespace(
        name="suggest_process_flow_activity_automation_tool",
        description="Sugere rascunhos de automação, conexão APP32/MCP/API e intervenção humana para uma atividade BPMN específica.",
    ),
    SimpleNamespace(
        name="list_process_improvement_requests_tool",
        description="Lista solicitações e análises da Central de Melhorias no tenant ativo.",
    ),
    SimpleNamespace(
        name="get_process_improvement_analysis_context_tool",
        description="Obtém briefing, contexto do processo e contrato estruturado para análise do Squad Cliente.",
    ),
    SimpleNamespace(
        name="submit_process_improvement_analysis_tool",
        description="Grava a sugestão estruturada do Squad Cliente após confirmação humana explícita.",
    ),
    SimpleNamespace(
        name="get_process_pop_step_media_context_tool",
        description="Retorna o contexto multimídia de um passo POP, incluindo vídeo curto, print e próximos passos recomendados.",
    ),
    SimpleNamespace(
        name="draft_process_pop_step_description_tool",
        description="Gera um rascunho inicial da descrição de um passo POP usando narração, vídeo curto, print e contexto da atividade.",
    ),
    SimpleNamespace(name="create_process_pop_step_for_bpmn_tool", description="Cria um passo POP vinculado a uma atividade BPMN do processo."),
    SimpleNamespace(name="attach_process_pop_step_static_image_tool", description="Anexa uma evidência estática JPG/PNG a um passo POP."),
    SimpleNamespace(
        name="get_strategy_identity_tool",
        description="Lê a identidade organizacional estruturada do tenant, com fallback MVV legado.",
    ),
    SimpleNamespace(
        name="get_organizational_identity_tool",
        description="Alias canônico consultivo para ler a identidade organizacional estruturada.",
    ),
    SimpleNamespace(
        name="upsert_strategy_identity_tool",
        description="Cria ou atualiza a identidade organizacional estruturada do tenant.",
    ),
    SimpleNamespace(
        name="upsert_organizational_identity_tool",
        description="Alias canônico consultivo para criar ou atualizar a identidade organizacional estruturada.",
    ),
    SimpleNamespace(
        name="get_process_strategy_profile_tool",
        description="Lê o perfil estratégico estruturado de um processo.",
    ),
    SimpleNamespace(
        name="get_process_strategic_profile_tool",
        description="Alias canônico consultivo para ler o perfil estratégico estruturado de um processo.",
    ),
    SimpleNamespace(
        name="upsert_process_strategy_profile_tool",
        description="Cria ou atualiza objetivo, dono, cliente, indicadores, criticidade, maturidade, SIPOC e políticas do processo.",
    ),
    SimpleNamespace(
        name="upsert_process_strategic_profile_tool",
        description="Alias canônico consultivo para criar ou atualizar o perfil estratégico estruturado de um processo.",
    ),
    SimpleNamespace(
        name="list_process_strategy_alignment_links_tool",
        description="Lista vínculos Processo -> objetivo/pilar/proposta/diferencial/competência/política.",
    ),
    SimpleNamespace(
        name="upsert_process_strategy_alignment_link_tool",
        description="Cria ou atualiza vínculo estratégico de processo para análise N1.",
    ),
    SimpleNamespace(
        name="delete_process_strategy_alignment_link_tool",
        description="Remove vínculo estratégico de processo dentro do tenant.",
    ),
    SimpleNamespace(
        name="list_indicator_line_of_sight_tool",
        description="Lista vínculos Indicador de processo -> Indicador corporativo.",
    ),
    SimpleNamespace(
        name="upsert_indicator_line_of_sight_tool",
        description="Cria ou atualiza linha de visada entre indicador de processo e corporativo.",
    ),
    SimpleNamespace(
        name="delete_indicator_line_of_sight_tool",
        description="Remove linha de visada de indicadores dentro do tenant.",
    ),
    SimpleNamespace(
        name="list_strategy_maturation_backlog_tool",
        description="Lista a zona de maturação S1-S2 estratégica com filtros de status, bloco, fonte e estado.",
    ),
    SimpleNamespace(
        name="review_strategy_maturation_item_tool",
        description="Aplica human-gate S2->S3 em item de maturação estratégica: confirm, reject ou hold.",
    ),
    SimpleNamespace(
        name="get_strategy_alignment_n1_readiness_tool",
        description="Retorna readiness de dados para a Análise N1 de alinhamento estratégico.",
    ),
    SimpleNamespace(
        name="get_strategic_alignment_n1_readiness_tool",
        description="Alias canônico consultivo para readiness da Análise N1 de alinhamento estratégico.",
    ),
    SimpleNamespace(
        name="get_structuring_journey_tool",
        description="Retorna a Jornada de Estruturação com blocos, sub-blocos, maturidade e gates.",
    ),
    SimpleNamespace(
        name="run_strategy_alignment_n1_analysis_tool",
        description="Executa mapa de alinhamento x desalinhamento entre processos e identidade organizacional.",
    ),
    SimpleNamespace(
        name="analyze_strategic_alignment_n1_tool",
        description="Alias canônico consultivo para executar a Análise N1 de alinhamento estratégico.",
    ),
    SimpleNamespace(
        name="get_real_estate_auction_settings_tool",
        description="Lê a configuração do módulo Leilões Imobiliários para a empresa.",
    ),
    SimpleNamespace(
        name="upsert_real_estate_auction_settings_tool",
        description="Habilita/desabilita e configura o módulo Leilões Imobiliários para a empresa.",
    ),
    SimpleNamespace(
        name="get_real_estate_auction_workspace_tool",
        description="Retorna workspace/resumo do módulo Leilões Imobiliários no tenant.",
    ),
    SimpleNamespace(
        name="list_real_estate_auction_properties_tool",
        description="Lista imóveis/leilões do módulo, sempre escopando por company_id.",
    ),
    SimpleNamespace(
        name="get_real_estate_auction_property_tool",
        description="Retorna detalhe de um imóvel/leilão com ficha financeira, diligência, eventos e anexos.",
    ),
    SimpleNamespace(
        name="create_real_estate_auction_property_tool",
        description="Cria um imóvel/leilão no tenant habilitado.",
    ),
    SimpleNamespace(
        name="update_real_estate_auction_property_tool",
        description="Atualiza um imóvel/leilão dentro do tenant.",
    ),
    SimpleNamespace(
        name="archive_real_estate_auction_property_tool",
        description="Arquiva logicamente um imóvel/leilão dentro do tenant.",
    ),
    SimpleNamespace(
        name="list_real_estate_auction_sources_tool",
        description="Lista fontes de captação/importação do tenant para o módulo Leilões Imobiliários.",
    ),
    SimpleNamespace(
        name="create_real_estate_auction_source_tool",
        description="Cria uma fonte de importação/captação do módulo no tenant.",
    ),
    SimpleNamespace(
        name="update_real_estate_auction_source_tool",
        description="Atualiza uma fonte de importação/captação do módulo no tenant.",
    ),
    SimpleNamespace(
        name="delete_real_estate_auction_source_tool",
        description="Remove logicamente uma fonte do módulo dentro do tenant.",
    ),
    SimpleNamespace(
        name="create_real_estate_auction_event_tool",
        description="Cria um evento de leilão vinculado a um imóvel do tenant.",
    ),
    SimpleNamespace(
        name="update_real_estate_auction_event_tool",
        description="Atualiza um evento de leilão existente no tenant.",
    ),
    SimpleNamespace(
        name="delete_real_estate_auction_event_tool",
        description="Remove um evento de leilão do imóvel dentro do tenant.",
    ),
    SimpleNamespace(
        name="upsert_real_estate_auction_financial_sheet_tool",
        description="Cria ou atualiza a ficha financeira de um imóvel do tenant.",
    ),
    SimpleNamespace(
        name="upsert_real_estate_auction_due_diligence_tool",
        description="Cria ou atualiza a ficha de diligência/posse/riscos do imóvel.",
    ),
    SimpleNamespace(
        name="create_real_estate_auction_attachment_tool",
        description="Registra metadado de anexo para um imóvel/leilão do tenant.",
    ),
    SimpleNamespace(
        name="delete_real_estate_auction_attachment_tool",
        description="Remove metadado de anexo de um imóvel/leilão no tenant.",
    ),
    SimpleNamespace(
        name="get_work_journey_board_tool",
        description="Retorna o quadro operacional da jornada por blocos de um colaborador.",
    ),
    SimpleNamespace(
        name="list_work_journey_blocks_tool",
        description="Lista os blocos de jornada de um colaborador.",
    ),
    SimpleNamespace(
        name="save_work_journey_block_tool",
        description="Cria ou atualiza um bloco da jornada operacional.",
    ),
    SimpleNamespace(
        name="list_work_journey_rules_tool",
        description="Lista as obrigações recorrentes configuradas para a jornada do colaborador.",
    ),
    SimpleNamespace(
        name="save_work_journey_rule_tool",
        description="Cria ou atualiza uma obrigação recorrente da jornada operacional.",
    ),
    SimpleNamespace(
        name="update_work_journey_item_tool",
        description="Atualiza status, bloco ou esforço real de uma tarefa da jornada.",
    ),
    SimpleNamespace(
        name="list_work_journey_manual_tasks_tool",
        description="Lista tarefas avulsas da jornada operacional.",
    ),
    SimpleNamespace(
        name="create_work_journey_manual_task_tool",
        description="Cria uma tarefa avulsa diretamente na agenda do colaborador.",
    ),
    SimpleNamespace(
        name="get_work_journey_agenda_tool",
        description="Retorna a agenda materializada da jornada operacional.",
    ),
    SimpleNamespace(
        name="move_work_journey_agenda_item_tool",
        description="Move item da agenda materializada dentro da jornada operacional.",
    ),
    SimpleNamespace(
        name="generate_work_journey_agenda_tool",
        description="Gera ou regenera a agenda materializada da jornada operacional.",
    ),
    SimpleNamespace(
        name="lock_work_journey_agenda_tool",
        description="Trava a agenda materializada da jornada operacional.",
    ),
    SimpleNamespace(
        name="unlock_work_journey_agenda_tool",
        description="Destrava a agenda materializada da jornada operacional.",
    ),
    SimpleNamespace(
        name="list_routine_journey_bindings_tool",
        description="Lista vínculos entre rotinas operacionais, colaboradores e blocos elegíveis.",
    ),
    SimpleNamespace(
        name="save_routine_journey_binding_tool",
        description="Cria ou atualiza vínculo entre rotina operacional e bloco da jornada.",
    ),
    SimpleNamespace(
        name="list_employee_process_routines_for_journey_tool",
        description="Lista rotinas de processo que o colaborador precisa encaixar na jornada.",
    ),
    SimpleNamespace(
        name="list_work_calendar_events_tool",
        description="Lista eventos do calendário operacional respeitando o escopo do colaborador.",
    ),
    SimpleNamespace(
        name="create_work_calendar_event_tool",
        description="Cria evento do calendário operacional com validação de visibilidade MCP.",
    ),
    SimpleNamespace(
        name="update_work_calendar_event_tool",
        description="Atualiza evento do calendário operacional com validação de visibilidade MCP.",
    ),
    SimpleNamespace(
        name="delete_work_calendar_event_tool",
        description="Exclui evento do calendário operacional com validação de visibilidade MCP.",
    ),
    SimpleNamespace(
        name="list_work_journey_task_inventory_tool",
        description="Lista tarefas da jornada classificadas em alocadas, não alocadas e atrasadas.",
    ),
    SimpleNamespace(
        name="get_work_journey_capacity_report_tool",
        description="Retorna capacidade operacional, capacidade tomada, ociosa e sobrecarga por colaborador/bloco.",
    ),
    SimpleNamespace(
        name="get_process_routines_analysis_tool",
        description="Retorna a análise operacional da página process-routines/analysis.",
    ),
    SimpleNamespace(
        name="get_efficiency_collaborators_analysis_tool",
        description="Retorna a análise de eficiência por colaborador da página efficiency-analysis.",
    ),
    *tuple(
        SimpleNamespace(
            name=tool_name,
            description=f"Capability MCP comercial registrada para {tool_name}.",
        )
        for tool_name in (
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
            "get_commercial_dashboard",
            "list_commercial_contracts",
            "get_commercial_contract_workspace",
            "create_commercial_contract",
            "update_commercial_contract_general",
            "suspend_commercial_contract",
            "close_commercial_contract",
            "delete_commercial_contract",
            "upsert_commercial_contract_financial_terms",
            "upsert_commercial_contract_fiscal_terms",
            "add_commercial_contract_item",
            "update_commercial_contract_item",
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
        )
    ),
    *tuple(
        SimpleNamespace(
            name=tool_name,
            description=description,
        )
        for tool_name, description in (
            ("bootstrap_session_context", "Resolve o contexto mínimo da sessão MCP para bootstrap de surface e tenant."),
            ("list_feature_catalog", "Lista o catálogo documental de features MCP autorizado para a surface atual."),
            ("get_feature_guide", "Retorna o guia operacional de uma feature MCP autorizada."),
            ("get_feature_examples", "Retorna exemplos de uso de uma feature MCP autorizada."),
            ("get_feature_constraints", "Retorna restrições e contexto obrigatório de uma feature MCP autorizada."),
            ("consultive_get_next_action", "Retorna a próxima ação determinística da maturidade assistida, com responsável, tools, critérios e gate."),
            ("consultive_get_front_context", "Retorna o contexto consolidado da frente consultiva no tenant."),
            ("consultive_get_front_evidence", "Lista evidências internas consideradas na frente consultiva."),
            ("consultive_get_front_gaps", "Lista gaps metodológicos e técnicos da frente consultiva."),
            ("consultive_get_methodology_guidance", "Retorna recomendações metodológicas Versus para análise assistida da frente."),
            ("consultive_resolve_protocol", "Resolve protocolo consultivo ativo, versionado e modificável por frente/subfase/audiência."),
            ("consultive_upsert_protocol", "Cria ou atualiza protocolo consultivo tenant-owned e versionado."),
            ("consultive_register_assisted_analysis", "Registra no APP32 o resultado trazido pela IA/CLI via MCP."),
            ("consultive_list_assisted_analyses", "Lista histórico tenant-safe de análises assistidas, protocolos, validações e decisões."),
            ("consultive_register_squad_validation", "Registra validação do Squad Cliente, Squad Versus ou Squad Engenharia."),
            ("consultive_register_consultant_decision", "Registra o gate humano do consultor antes da conversão operacional."),
            ("consultive_create_recommended_action", "Registra intenção de conversão após decisão humana do consultor."),
            ("describe_app32_analysis_catalog_tool", "Descreve o catálogo analítico governado do APP32."),
            ("describe_app32_crud_contracts_tool", "Descreve contratos CRUD MCP por domínio canônico do APP32."),
            ("describe_app32_domain_examples_tool", "Descreve exemplos de uso por domínio MCP."),
            ("describe_app32_domain_playbooks_tool", "Descreve playbooks canônicos por domínio MCP."),
            ("describe_app32_external_ai_onboarding_tool", "Descreve onboarding seguro de IA externa no MCP."),
            ("describe_app32_external_llm_factory_surface_tool", "Descreve a surface da factory de LLM externo."),
            ("describe_app32_implantation_persona_profile_tool", "Descreve perfis de persona de implantação do APP32."),
            ("preview_app32_implantation_persona_profile_update_tool", "Pré-visualiza atualização de perfil/persona de implantação."),
            ("apply_app32_implantation_persona_profile_update_tool", "Aplica atualização governada de perfil/persona de implantação."),
            ("describe_app32_instruction_registry_tool", "Descreve o instruction registry canônico do runtime."),
            ("resolve_app32_instruction_bundle_tool", "Resolve bundle de instruções por runtime, surface e perfil."),
            ("describe_app32_operational_readiness_tool", "Descreve readiness operacional para abertura controlada IA/MCP."),
            ("describe_app32_permission_matrix_tool", "Descreve a permission matrix canônica por surface e perfil."),
            ("describe_app32_profile_contracts_tool", "Descreve contratos canônicos de perfil MCP."),
            ("describe_app32_release_checklist_tool", "Descreve checklist de release e smoke pós-deploy IA/MCP."),
            ("describe_app32_sapiens_factory_tool", "Descreve a Sapiens Factory e seu catálogo de capabilities."),
            ("assess_app32_change_request_tool", "Avalia solicitação de mudança APP32 sob critérios de capability e risco."),
            ("trace_app32_capability_dependencies_tool", "Rastreia dependências de uma capability APP32."),
            ("describe_app32_available_sapiens_squads_tool", "Lista squads Sapiens disponíveis e critérios de ativação."),
            ("resolve_app32_sapiens_activation_tool", "Resolve ativação governada de squad Sapiens."),
            ("describe_app32_session_company_scope_tool", "Descreve escopo de empresa da sessão MCP."),
            ("describe_app32_session_harness_tool", "Descreve o harness especialista ativo da sessão MCP."),
            ("select_app32_session_harness_tool", "Ativa um harness oficial do mesmo Squad Cliente."),
            ("resolve_app32_operation_tool", "Resolve domínio, intenção, harness e tool ativa sem varrer catálogos."),
            ("select_app32_session_company_tool", "Seleciona empresa ativa da sessão MCP quando permitido."),
            ("clear_app32_session_company_tool", "Limpa a empresa ativa da sessão MCP."),
            ("describe_app32_squad_runtime_tool", "Descreve runtime de squads e harnesses oficiais."),
            ("describe_app32_surface_playbooks_tool", "Descreve playbooks por surface MCP."),
            ("describe_app32_tool_freeze_procedure_tool", "Descreve procedimento de congelamento de tool insegura."),
            ("describe_app32_usage_dashboard_tool", "Descreve dashboard de uso IA/MCP e métricas publicadas."),
            ("evaluate_app32_external_llm_factory_session_tool", "Avalia uma sessão de LLM externo conforme factory e políticas."),
            ("list_app32_integrations_catalog", "Lista integrações disponíveis no catálogo APP32."),
            ("request_new_app32_integration", "Solicita nova integração APP32 para backlog governado."),
            ("get_incentive_indicators", "Consulta indicadores de incentivo e metas do tenant."),
            ("get_strategic_connection_graph", "Expõe a Teia de Conexões como grafo analítico tenant-safe."),
            ("get_strategic_connection_metrics", "Calcula métricas executivas da Teia de Conexões."),
            ("generate_strategic_connection_summary", "Gera relatório sucinto com gaps e recomendações da Teia."),
            ("list_work_journey_absences_tool", "Lista ausências registradas na jornada operacional."),
            ("create_work_journey_absence_request_tool", "Cria solicitação de ausência na jornada operacional."),
            ("approve_work_journey_absence_request_tool", "Aprova solicitação de ausência da jornada operacional."),
            ("list_work_journey_transfers_tool", "Lista transferências da jornada operacional."),
            ("create_work_journey_transfer_request_tool", "Cria solicitação de transferência na jornada operacional."),
            ("approve_work_journey_transfer_request_tool", "Aprova solicitação de transferência da jornada operacional."),
            ("delete_work_journey_block_tool", "Remove bloco da jornada operacional com governança."),
            ("delete_work_journey_rule_tool", "Remove regra recorrente da jornada operacional com governança."),
            ("delete_work_journey_manual_task_tool", "Remove tarefa manual da jornada operacional com governança."),
        )
    ),
    *tuple(
        SimpleNamespace(
            name=tool_name,
            description=f"Capability MCP financeira registrada para {tool_name}.",
        )
        for tool_name in (
            "list_financial_catalog_items",
            "create_financial_catalog_item",
            "update_financial_catalog_item",
            "toggle_financial_catalog_item",
            "list_financial_domain_enablements",
            "upsert_financial_domain_enablement",
            "toggle_financial_domain_enablement",
            "list_financial_ingestion_records",
            "create_financial_ingestion_record",
            "review_financial_ingestion_record",
            "convert_financial_ingestion_record",
            "list_financial_schedules",
            "get_financial_payables_due_summary",
            "create_financial_schedule",
            "update_financial_schedule",
            "toggle_financial_schedule",
            "generate_due_financial_schedules",
            "list_financial_borderos",
            "get_financial_bordero",
            "create_financial_bordero",
            "create_financial_bordero_settlement",
            "get_financial_budget_planning_workspace",
            "get_financial_budget_execution_workspace",
            "create_financial_budget_line",
            "create_financial_budget_contract",
            "create_financial_budget_document",
            "create_financial_budget_document_schedules",
            "list_financial_automation_rules",
            "create_financial_automation_rule",
            "apply_financial_automation_to_instance",
            "list_financial_automation_executions",
            "dispatch_financial_process_trigger",
            "list_financial_entries",
            "get_financial_entry",
            "create_financial_entry",
            "create_financial_direct_entry",
            "replace_financial_allocations",
            "create_financial_settlement",
            "list_financial_import_batches",
            "get_financial_import_batch",
            "create_financial_import_batch",
            "process_financial_import_batch",
            "reconcile_financial_import_batch",
            "review_financial_reconciliation_match",
            "get_financial_bank_reconciliation_overview",
            "get_financial_bank_reconciliation_workspace",
            "list_financial_bank_reconciliation_candidates",
            "match_financial_bank_reconciliation_row",
            "create_financial_entry_from_bank_reconciliation_row",
            "list_financial_classification_rules",
            "create_financial_classification_rule",
            "update_financial_classification_rule",
            "toggle_financial_classification_rule",
            "classify_financial_import_batch",
            "list_financial_classification_memories",
            "update_financial_classification_memory",
            "toggle_financial_classification_memory",
            "suggest_financial_classification_for_batch",
            "list_financial_classification_suggestions",
            "review_financial_classification_suggestion",
            "ai_rank_financial_classification",
            "list_financial_classification_pending",
            "get_financial_classification_dashboard",
            "list_financial_closings",
            "create_financial_closing",
            "list_financial_report_types",
            "generate_financial_report",
            "get_financial_executive_dashboard",
            "list_financial_budget_versions",
            "create_financial_budget_version",
            "duplicate_financial_budget_version",
            "get_financial_budget_matrix",
            "upsert_financial_budget_matrix",
            "import_financial_budget_matrix",
            "ask_user_for_financial_classification",
            "resolve_financial_classification_answer",
        )
    ),
)

_langchain_tools = tuple(legacy_langchain_tools) + tuple(knowledge_langchain_tools)

_legacy_tool_registry = ToolCapabilityRegistry.from_tools(
    _langchain_tools + _supplemental_mcp_tools
)

catalog = ToolCatalog(
    langchain_tools=_langchain_tools,
    mcp_registrars=tuple(
        registrar
        for registrar in (
        register_analysis_catalog_tools,
        register_commercial_mcp_tools,
        register_consultive_assisted_analysis_tools,
        register_crud_contract_tools,
        register_domain_example_tools,
        register_domain_playbook_tools,
        register_external_ai_onboarding_tools,
        register_feature_catalog_tools,
        register_external_llm_factory_tools,
        register_financial_mcp_tools,
        register_implantation_persona_profile_tools,
        register_incentive_tools,
        register_integration_request_tools,
        register_instruction_registry_tools,
        register_knowledge_tools,
        register_strategic_tree_tools,
        register_operational_readiness_tools,
        register_operation_router_tools,
        register_permission_matrix_tools,
        register_plan_driver_tools,
        register_plan_global_okr_tools,
        register_plan_global_okr_correction_tools,
        register_plan_participant_tools,
        register_process_flow_tools,
        register_process_improvement_tools,
        register_process_pop_tools,
        register_profile_contract_tools,
        register_real_estate_auction_tools,
        register_release_checklist_tools,
        register_sector_strategy_tools,
        register_sapiens_activation_tools,
        register_sapiens_factory_tools,
        register_session_company_tools,
        register_session_harness_tools,
        register_squad_runtime_tools,
        register_strategy_alignment_tools,
        register_surface_playbook_tools,
        register_tool_freeze_tools,
        register_usage_dashboard_tools,
        register_work_journey_analytics_tools,
        register_work_journey_tools,
        )
        if registrar is not None
    ),
    capability_registry=_legacy_tool_registry,
)

# Compatibilidade legada: vários módulos ainda importam `tools`.
tools = catalog.get_langchain_tools()
