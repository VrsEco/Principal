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
from src.intelligence.tools import tools as legacy_langchain_tools
from src.core.mcp_analysis_catalog_tools import register_analysis_catalog_tools
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
from src.core.mcp_operational_readiness_tools import register_operational_readiness_tools
from src.core.mcp_permission_matrix_tools import register_permission_matrix_tools
from src.core.mcp_process_flow_tools import register_process_flow_tools
from src.core.mcp_process_pop_tools import register_process_pop_tools
from src.core.mcp_profile_contract_tools import register_profile_contract_tools
from src.core.mcp_real_estate_auction_tools import register_real_estate_auction_tools
from src.core.mcp_release_checklist_tools import register_release_checklist_tools
from src.core.mcp_sapiens_activation_tools import register_sapiens_activation_tools
from src.core.mcp_sapiens_factory_tools import register_sapiens_factory_tools
from src.core.mcp_session_company_tools import register_session_company_tools
from src.core.mcp_squad_runtime_tools import register_squad_runtime_tools
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
    SimpleNamespace(
        name="analyze_process_flow_copilot_tool",
        description="Analisa o fluxo BPMN do processo e aponta gaps de lane, POP, gateways e oportunidades de automação/conexão.",
    ),
    SimpleNamespace(
        name="suggest_process_flow_activity_automation_tool",
        description="Sugere rascunhos de automação, conexão APP32/MCP/API e intervenção humana para uma atividade BPMN específica.",
    ),
    SimpleNamespace(
        name="get_process_pop_step_media_context_tool",
        description="Retorna o contexto multimídia de um passo POP, incluindo vídeo curto, print e próximos passos recomendados.",
    ),
    SimpleNamespace(
        name="draft_process_pop_step_description_tool",
        description="Gera um rascunho inicial da descrição de um passo POP usando narração, vídeo curto, print e contexto da atividade.",
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

_legacy_tool_registry = ToolCapabilityRegistry.from_tools(
    tuple(legacy_langchain_tools) + _supplemental_mcp_tools
)

catalog = ToolCatalog(
    langchain_tools=tuple(legacy_langchain_tools),
    mcp_registrars=tuple(
        registrar
        for registrar in (
        register_analysis_catalog_tools,
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
        register_operational_readiness_tools,
        register_permission_matrix_tools,
        register_process_flow_tools,
        register_process_pop_tools,
        register_profile_contract_tools,
        register_real_estate_auction_tools,
        register_release_checklist_tools,
        register_sapiens_activation_tools,
        register_sapiens_factory_tools,
        register_session_company_tools,
        register_squad_runtime_tools,
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
