"""Coortes de ESCRITA do mcp-versus (onda 2), no molde das coortes de leitura.

Cada coorte é um assunto. A variável ``MCP_VERSUS_WRITE_DOMAINS`` no ambiente do servidor liga os assuntos
(``projects,operations,meetings``); ausente, vazia ou ``none`` mantém tudo desligado. Assunto desligado não é
listado nem registrado. A porta de entrada é o contrato de mutações: só entra numa coorte a ferramenta sem
violação na linha de base (``tests/data/mcp_mutation_violations_baseline.json``).

A aprovação humana segue a regra D6 (``mcp_gate_policy``) e é aplicada pelo runtime.
"""

from __future__ import annotations

import os

ENV_DOMAINS = "MCP_VERSUS_WRITE_DOMAINS"

# Sub-ondas 2A a 2E e admin_ops (SPEC onda2_mutacoes_mcp_versus_v1, seção 9).
WRITE_COHORT_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    "projects": (
        "create_project",
        "update_project",
        "update_project_task_secure",
    ),
    "operations": (
        "request_engineering_suggestion",
        "request_new_app32_integration",
    ),
    "meetings": (
        "log_meeting_discussion",
    ),
    # Sub-onda 2B: modelagem de processos (BPMN e POP). Ficam fora: publicação do pacote de modelagem
    # (escopo ainda inalcançável por token comum) e as duas financeiras (sub-onda 2F).
    "processes": (
        "create_process_bpmn_activity_tool",
        "create_process_pop_step_for_bpmn_tool",
        "draft_process_pop_step_description_tool",
        "attach_process_pop_step_static_image_tool",
        "update_process_instance",
    ),
    # Sub-onda 2C: jornada de trabalho. Fora: aprovações (escopo ainda inalcançável por token comum), exclusões de alto risco e as legadas do chat (complete_task, log_work_hours).
    "routine": (
        "create_work_calendar_event_tool",
        "create_work_journey_absence_request_tool",
        "create_work_journey_manual_task_tool",
        "create_work_journey_transfer_request_tool",
        "delete_work_calendar_event_tool",
        "generate_work_journey_agenda_tool",
        "lock_work_journey_agenda_tool",
        "move_work_journey_agenda_item_tool",
        "save_routine_journey_binding_tool",
        "save_work_journey_block_tool",
        "save_work_journey_rule_tool",
        "unlock_work_journey_agenda_tool",
        "update_work_calendar_event_tool",
        "update_work_journey_item_tool",
    ),
    # Sub-onda 2D: estratégia. Fora: exclusões de vínculo e de linha de visada (alto risco, escopo só admin).
    "strategy": (
        "correct_plan_global_okrs_tool",
        "create_and_link_plan_global_okrs_tool",
        "create_area_key_result",
        "create_area_okr",
        "create_global_key_result",
        "create_global_okr",
        "create_sector_okr_structure_tool",
        "create_single_plan_driver_tool",
        "review_strategy_maturation_item_tool",
        "sync_plan_participants_tool",
        "update_plan_section",
        "upsert_indicator_line_of_sight_tool",
        "upsert_organizational_identity_tool",
        "upsert_process_strategic_profile_tool",
        "upsert_process_strategy_alignment_link_tool",
        "upsert_process_strategy_profile_tool",
        "upsert_strategy_identity_tool",
    ),
    # Sub-onda 2E: contratos, catálogo e cadastros comerciais. Encerrar contrato exige aprovação pela regra D6. Fora: excluir contrato, financeiras do faturamento e fiscal (2F), deploy de agentes.
    "commercial": (
        "add_commercial_contract_item",
        "close_commercial_contract",
        "create_commercial_contract",
        "create_commercial_issuer",
        "toggle_commercial_catalog_structure_item",
        "toggle_commercial_customer_portfolio",
        "toggle_commercial_product_service",
        "update_commercial_catalog_structure_item",
        "update_commercial_contract_general",
        "update_commercial_contract_item",
        "update_commercial_customer",
        "update_commercial_customer_portfolio",
        "update_commercial_issuer",
        "update_commercial_offer_contract",
        "update_commercial_product_service",
    ),
    # Sub-onda admin_ops: aprovações e exclusões que já exigem aprovação humana persistida (regra D6) e permissão por
    # empresa; só aparecem para quem tem a permissão. Fora: usuários, status de empresa, agentes, WhatsApp, diagnósticos.
    "admin_ops": (
        "approve_work_journey_absence_request_tool",
        "approve_work_journey_transfer_request_tool",
        "delete_indicator_line_of_sight_tool",
        "delete_process_strategy_alignment_link_tool",
        "delete_work_journey_block_tool",
        "delete_work_journey_manual_task_tool",
        "delete_work_journey_rule_tool",
    ),
}


def enabled_write_domains() -> frozenset[str]:
    raw = os.environ.get(ENV_DOMAINS)
    if raw is None:
        return frozenset()
    parts = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return frozenset() if "none" in parts else frozenset(parts)


def all_write_cohort_names() -> tuple[str, ...]:
    return tuple(name for names in WRITE_COHORT_TOOL_NAMES.values() for name in names)


def enabled_write_cohort_names() -> tuple[str, ...]:
    enabled = enabled_write_domains()
    return tuple(name for domain, names in WRITE_COHORT_TOOL_NAMES.items() if domain in enabled for name in names)
