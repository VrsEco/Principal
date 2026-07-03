from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Iterable

from models import (
    Employee,
    IncentiveGovernabilityMatrix,
    IncentiveRuleSet,
    Indicator,
    IndicatorData,
    IndicatorEntityLink,
    IndicatorGoal,
    IndicatorLineOfSight,
    MacroProcess,
    Plan,
    PlanSectionStatus,
    Process,
    ProcessActivityExecutionContract,
    ProcessArea,
    ProcessBpmnDiagram,
    ProcessRoutine,
    ProcessStep,
    ProcessStrategyProfile,
    Role,
    StrategyMaturationItem,
)
from services.strategy_alignment_n1_service import StrategyAlignmentN1Error, StrategyAlignmentN1Service


class StructuringJourneyService:
    """Read model tenant-safe da Jornada de Estruturação Sapiens.

    Camada de jornada sobre a maturação N1: não cria novo estado transacional,
    apenas agrega identidade, arquitetura, modelagem e backlog S1-S2.
    """

    JOURNEY_KEY = "sapiens_structuring"
    READ_MODEL = "sapiens.structuring_journey"
    VERSION = "v1"
    GATE_POLICY = "soft"

    IDENTITY_SUBBLOCK_FIELDS = {
        "mission": ("mission",),
        "vision": ("vision",),
        "values": ("values",),
        "positioning": ("positioning", "value_propositions", "differentials", "segments_icp"),
        "org_chart": ("org_chart", "_org_chart_present"),
    }

    PROCESS_PROFILE_FIELDS = {
        "process_owner": ("owner", "owner_employee_id"),
        "process_objective": ("objective",),
        "criticality": ("strategic_criticality",),
        "customer_served": ("customer_type", "customer_description"),
        "process_indicators": ("indicators",),
        "sipoc": ("sipoc",),
        "regulatory_risk": ("regulatory_exposure", "risks"),
        "cost_volume": ("cost_resources_volume",),
    }

    REGISTRY = {
        "journey_key": JOURNEY_KEY,
        "version": VERSION,
        "gate_policy": GATE_POLICY,
        "blocks": [
            {
                "key": "identity",
                "order": 1,
                "label": "Identidade Organizacional",
                "client_label": "Monte o DNA da sua empresa",
                "consultant_label": "Identidade Organizacional",
                "subblocks": [
                    ("mission", "Missão", "essential"),
                    ("vision", "Visão", "essential"),
                    ("values", "Valores", "essential"),
                    ("positioning", "Posicionamento", "essential"),
                    ("org_chart", "Organograma", "essential"),
                ],
            },
            {
                "key": "processes",
                "order": 2,
                "label": "Processos",
                "client_label": "Organize como a empresa funciona",
                "consultant_label": "Processos",
                "subblocks": [
                    ("architecture", "Arquitetura", "essential"),
                    ("modeling", "Modelagem", "essential"),
                    ("implementation", "Implantação", "essential"),
                    ("stabilization", "Estabilização", "essential"),
                    ("audit", "Auditoria", "essential"),
                ],
            },
            {
                "key": "growth_plan",
                "order": 3,
                "label": "Planejamento Estratégico",
                "client_label": "Direcione o crescimento",
                "consultant_label": "Planejamento Estratégico",
                "subblocks": [
                    ("structured", "Estruturado", "essential"),
                    ("connected", "Conectado", "essential"),
                    ("deployed", "Desdobrado", "essential"),
                    ("linked_to_management", "Vinculado à gestão", "essential"),
                ],
            },
            {
                "key": "strategic_management",
                "order": 4,
                "label": "Gerenciamento Estratégico",
                "client_label": "Faça a estratégia rodar",
                "consultant_label": "Gerenciamento Estratégico",
                "subblocks": [
                    ("indicators", "Indicadores", "essential"),
                    ("cycles", "Ciclos", "essential"),
                    ("incentives", "Incentivos", "essential"),
                    ("connection_web", "Teia de Conexões", "essential"),
                ],
            },
        ],
    }

    @staticmethod
    def get_journey(
        company_id: int,
        *,
        audience: str | None = "client",
        scope: str | None = "company",
        process_id: int | None = None,
    ) -> dict[str, Any]:
        StrategyAlignmentN1Service._require_company(company_id)

        normalized_scope = str(scope or "company").strip().lower()
        if normalized_scope not in {"company", "process"}:
            raise StrategyAlignmentN1Error("scope inválido. Use company ou process.")

        identity = StrategyAlignmentN1Service.get_identity(company_id, status="confirmed")
        identity = StructuringJourneyService._with_org_chart_evidence(company_id, dict(identity or {}))
        maturation_items = [row.to_dict() for row in StrategyMaturationItem.query.filter_by(company_id=company_id).all()]

        process_query = Process.query.filter_by(company_id=company_id)
        if hasattr(Process, "is_active"):
            process_query = process_query.filter(Process.is_active.isnot(False))
        if process_id:
            process_query = process_query.filter(Process.id == int(process_id))
        processes = [StructuringJourneyService._process_payload(row) for row in process_query.all()]
        if process_id and not processes:
            raise StrategyAlignmentN1Error(
                f"Processo não encontrado no tenant informado: company_id={company_id}, process_id={process_id}."
            )

        process_ids = {int(item["id"]) for item in processes if item.get("id") is not None}
        profiles = [
            row.to_dict()
            for row in ProcessStrategyProfile.query.filter_by(company_id=company_id).all()
            if not process_ids or int(row.process_id) in process_ids
        ]
        bpmn_diagrams = [
            StructuringJourneyService._bpmn_payload(row)
            for row in ProcessBpmnDiagram.query.filter_by(company_id=company_id).all()
            if not process_ids or int(row.process_id) in process_ids
        ]
        routines = [
            StructuringJourneyService._routine_payload(row)
            for row in ProcessRoutine.query.filter_by(company_id=company_id).all()
            if (not process_ids or int(row.process_id) in process_ids) and bool(getattr(row, "is_active", True))
        ]
        routine_ids = [int(item["id"]) for item in routines if item.get("id") is not None]
        process_steps = [
            StructuringJourneyService._step_payload(row)
            for row in (ProcessStep.query.filter(ProcessStep.routine_id.in_(routine_ids)).all() if routine_ids else [])
        ]
        contracts = [
            row.to_dict()
            for row in ProcessActivityExecutionContract.query.filter_by(company_id=company_id).all()
            if (not process_ids or int(row.process_id) in process_ids) and bool(getattr(row, "is_active", True))
        ]
        growth_plans = [row.to_dict() for row in Plan.query.filter_by(company_id=company_id, mode="growth").all()]
        growth_plan_ids = [int(item["id"]) for item in growth_plans if item.get("id") is not None]
        plan_section_statuses = [
            row.to_dict()
            for row in (
                PlanSectionStatus.query.filter(PlanSectionStatus.plan_id.in_(growth_plan_ids)).all()
                if growth_plan_ids
                else []
            )
        ]
        indicators = [
            row.to_dict()
            for row in Indicator.query.filter_by(company_id=company_id).all()
            if bool(getattr(row, "is_active", True))
        ]
        indicator_ids = [int(item["id"]) for item in indicators if item.get("id") is not None]
        indicator_data = [
            row.to_dict()
            for row in (
                IndicatorData.query.filter(IndicatorData.company_id == company_id, IndicatorData.indicator_id.in_(indicator_ids)).all()
                if indicator_ids
                else []
            )
        ]
        indicator_goals = [
            row.to_dict()
            for row in (
                IndicatorGoal.query.filter(IndicatorGoal.company_id == company_id, IndicatorGoal.indicator_id.in_(indicator_ids)).all()
                if indicator_ids
                else []
            )
        ]
        indicator_links = [row.to_dict() for row in IndicatorEntityLink.query.filter_by(company_id=company_id).all()]
        line_of_sight = [row.to_dict() for row in IndicatorLineOfSight.query.filter_by(company_id=company_id).all()]
        incentive_rule_sets = [
            row.to_dict()
            for row in IncentiveRuleSet.query.filter_by(company_id=company_id).all()
            if bool(getattr(row, "is_active", True)) and not getattr(row, "deleted_at", None)
        ]
        incentive_governability = [
            {
                "id": row.id,
                "role_id": row.role_id,
                "indicator_id": row.indicator_id,
                "governability_level": row.governability_level,
            }
            for row in IncentiveGovernabilityMatrix.query.filter_by(company_id=company_id).all()
        ]

        if process_ids:
            macro_ids = {int(item["macro_id"]) for item in processes if item.get("macro_id") is not None}
            macros = [
                StructuringJourneyService._macro_payload(row)
                for row in MacroProcess.query.filter_by(company_id=company_id).all()
                if int(row.id) in macro_ids
            ]
            area_ids = {int(item["area_id"]) for item in macros if item.get("area_id") is not None}
            areas = [
                StructuringJourneyService._area_payload(row)
                for row in ProcessArea.query.filter_by(company_id=company_id).all()
                if int(row.id) in area_ids
            ]
        else:
            areas = [StructuringJourneyService._area_payload(row) for row in ProcessArea.query.filter_by(company_id=company_id).all()]
            macros = [StructuringJourneyService._macro_payload(row) for row in MacroProcess.query.filter_by(company_id=company_id).all()]

        return StructuringJourneyService.build_structuring_journey_from_records(
            company_id=company_id,
            audience=audience,
            scope=normalized_scope,
            process_id=process_id,
            identity=identity,
            process_areas=areas,
            macro_processes=macros,
            processes=processes,
            profiles=profiles,
            bpmn_diagrams=bpmn_diagrams,
            routines=routines,
            process_steps=process_steps,
            execution_contracts=contracts,
            maturation_items=maturation_items,
            growth_plans=growth_plans,
            plan_section_statuses=plan_section_statuses,
            indicators=indicators,
            indicator_data=indicator_data,
            indicator_goals=indicator_goals,
            indicator_links=indicator_links,
            line_of_sight=line_of_sight,
            incentive_rule_sets=incentive_rule_sets,
            incentive_governability=incentive_governability,
        )

    @staticmethod
    def build_structuring_journey_from_records(
        *,
        company_id: int,
        identity: dict[str, Any],
        process_areas: list[dict[str, Any]],
        macro_processes: list[dict[str, Any]],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        bpmn_diagrams: list[dict[str, Any]],
        routines: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
        execution_contracts: list[dict[str, Any]],
        maturation_items: list[dict[str, Any]],
        growth_plans: list[dict[str, Any]] | None = None,
        plan_section_statuses: list[dict[str, Any]] | None = None,
        indicators: list[dict[str, Any]] | None = None,
        indicator_data: list[dict[str, Any]] | None = None,
        indicator_goals: list[dict[str, Any]] | None = None,
        indicator_links: list[dict[str, Any]] | None = None,
        line_of_sight: list[dict[str, Any]] | None = None,
        incentive_rule_sets: list[dict[str, Any]] | None = None,
        incentive_governability: list[dict[str, Any]] | None = None,
        audience: str | None = "client",
        scope: str | None = "company",
        process_id: int | None = None,
    ) -> dict[str, Any]:
        growth_plans = growth_plans or []
        plan_section_statuses = plan_section_statuses or []
        indicators = indicators or []
        indicator_data = indicator_data or []
        indicator_goals = indicator_goals or []
        indicator_links = indicator_links or []
        line_of_sight = line_of_sight or []
        incentive_rule_sets = incentive_rule_sets or []
        incentive_governability = incentive_governability or []
        blocks: list[dict[str, Any]] = []
        previous_ready = True
        current_block_key: str | None = None
        unlocked_until_order = 0

        for block_def in StructuringJourneyService.REGISTRY["blocks"]:
            block_key = block_def["key"]
            subblocks = [
                StructuringJourneyService._build_subblock(
                    block_key=block_key,
                    key=sub_key,
                    label=label,
                    criticality=criticality,
                    identity=identity,
                    process_areas=process_areas,
                    macro_processes=macro_processes,
                    processes=processes,
                    profiles=profiles,
                    bpmn_diagrams=bpmn_diagrams,
                    routines=routines,
                    process_steps=process_steps,
                    execution_contracts=execution_contracts,
                    maturation_items=maturation_items,
                    growth_plans=growth_plans,
                    plan_section_statuses=plan_section_statuses,
                    indicators=indicators,
                    indicator_data=indicator_data,
                    indicator_goals=indicator_goals,
                    indicator_links=indicator_links,
                    line_of_sight=line_of_sight,
                    incentive_rule_sets=incentive_rule_sets,
                    incentive_governability=incentive_governability,
                )
                for sub_key, label, criticality in block_def["subblocks"]
            ]
            essential_missing = [
                {
                    "key": item["key"],
                    "label": item["label"],
                    "status": item["status"],
                    "missing_to_ready": item["missing_to_ready"],
                }
                for item in subblocks
                if item["criticality"] == "essential" and not item["ready"]
            ]
            block_ready = not essential_missing
            unlocked = previous_ready
            if unlocked:
                unlocked_until_order = int(block_def["order"])
            if current_block_key is None and not block_ready:
                current_block_key = block_key

            block_maturity_scores = [item["maturity_pct"] for item in subblocks if item["maturity_pct"] is not None]
            blocks.append(
                {
                    "key": block_key,
                    "order": block_def["order"],
                    "label": block_def["label"],
                    "client_label": block_def["client_label"],
                    "consultant_label": block_def["consultant_label"],
                    "unlocked": unlocked,
                    "locked_for_client": not unlocked,
                    "write_blocked": False,
                    "maturity_pct": StructuringJourneyService._average(block_maturity_scores),
                    "gate": {
                        "policy": StructuringJourneyService.GATE_POLICY,
                        "ready": block_ready,
                        "required_criticality": "essential",
                        "missing_essentials": essential_missing,
                        "message": (
                            "Fase pronta para avançar."
                            if block_ready
                            else "Complete os sub-blocos essenciais para destravar a próxima fase."
                        ),
                    },
                    "subblocks": subblocks,
                }
            )
            previous_ready = previous_ready and block_ready

        if current_block_key is None:
            current_block_key = blocks[-1]["key"] if blocks else None
        overall_scores = [block["maturity_pct"] for block in blocks if block["maturity_pct"] is not None]
        ready_blocks = [block for block in blocks if block["gate"]["ready"]]
        return {
            "company_id": company_id,
            "journey_key": StructuringJourneyService.JOURNEY_KEY,
            "read_model": StructuringJourneyService.READ_MODEL,
            "version": StructuringJourneyService.VERSION,
            "gate_policy": StructuringJourneyService.GATE_POLICY,
            "audience": str(audience or "client"),
            "scope": str(scope or "company"),
            "process_id": process_id,
            "current_block": current_block_key,
            "unlocked_until_order": unlocked_until_order,
            "summary": {
                "overall_maturity_pct": StructuringJourneyService._average(overall_scores),
                "blocks_total": len(blocks),
                "blocks_ready": len(ready_blocks),
                "blocks_unlocked": sum(1 for block in blocks if block["unlocked"]),
                "subblocks_total": sum(len(block["subblocks"]) for block in blocks),
                "pending_items": sum(int(item.get("pending_count") or 0) for block in blocks for item in block["subblocks"]),
                "next_missing": next(
                    (
                        block["gate"]["missing_essentials"]
                        for block in blocks
                        if block["key"] == current_block_key
                    ),
                    [],
                ),
            },
            "methodology_alignment": {
                "canonical_driver": "consultive_cockpit",
                "canonical_url": "/consultive/cockpit",
                "layer": "camada_consultiva_evolutiva",
                "legacy_blocks_are_auxiliary": True,
                "note": (
                    "A Jornada/Maturação N1 é evidência auxiliar. A condução consultiva oficial "
                    "das frentes, fases e gates ocorre no Cockpit do Consultor."
                ),
            },
            "method_phases": StructuringJourneyService._method_phases(),
            "blocks": blocks,
        }

    @staticmethod
    def _method_phases() -> list[dict[str, Any]]:
        return [
            {
                "number": "00",
                "title": "Base Organizacional",
                "gate": "Base organizacional minimamente clara e empresa minimamente na mão.",
                "fronts": ["identity", "processes", "strategic_management"],
            },
            {
                "number": "01",
                "title": "Processos Finalísticos",
                "gate": "Cadeia de valor principal estabilizada por evidência operacional.",
                "fronts": ["processes"],
            },
            {
                "number": "02",
                "title": "Todos os Processos",
                "gate": "Operação inteira sob lógica de processo, indicador e formação progressiva de gestão.",
                "fronts": ["processes", "strategic_management"],
            },
            {
                "number": "03",
                "title": "Estratégia Rodando",
                "gate": "Estratégia em ciclo vivo de gestão, com planejamento, decisões, indicadores e projetos conectados.",
                "fronts": ["identity", "growth_plan", "strategic_management"],
            },
        ]

    @staticmethod
    def _build_subblock(
        *,
        block_key: str,
        key: str,
        label: str,
        criticality: str,
        identity: dict[str, Any],
        process_areas: list[dict[str, Any]],
        macro_processes: list[dict[str, Any]],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        bpmn_diagrams: list[dict[str, Any]],
        routines: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
        execution_contracts: list[dict[str, Any]],
        maturation_items: list[dict[str, Any]],
        growth_plans: list[dict[str, Any]],
        plan_section_statuses: list[dict[str, Any]],
        indicators: list[dict[str, Any]],
        indicator_data: list[dict[str, Any]],
        indicator_goals: list[dict[str, Any]],
        indicator_links: list[dict[str, Any]],
        line_of_sight: list[dict[str, Any]],
        incentive_rule_sets: list[dict[str, Any]],
        incentive_governability: list[dict[str, Any]],
    ) -> dict[str, Any]:
        required_count, confirmed_count, evidence = StructuringJourneyService._canonical_evidence(
            block_key=block_key,
            key=key,
            identity=identity,
            process_areas=process_areas,
            macro_processes=macro_processes,
            processes=processes,
            profiles=profiles,
            bpmn_diagrams=bpmn_diagrams,
            routines=routines,
            process_steps=process_steps,
            execution_contracts=execution_contracts,
            growth_plans=growth_plans,
            plan_section_statuses=plan_section_statuses,
            indicators=indicators,
            indicator_data=indicator_data,
            indicator_goals=indicator_goals,
            indicator_links=indicator_links,
            line_of_sight=line_of_sight,
            incentive_rule_sets=incentive_rule_sets,
            incentive_governability=incentive_governability,
        )
        counts = StructuringJourneyService._maturation_counts(block_key, key, maturation_items)
        if required_count > 0 and counts.get("confirmed", 0):
            confirmed_count = max(confirmed_count, min(required_count, int(counts.get("confirmed", 0))))
        maturity_pct = StructuringJourneyService._pct(confirmed_count, required_count)
        ready = bool(required_count > 0 and confirmed_count >= required_count)
        status = StructuringJourneyService._subblock_status(
            ready=ready,
            confirmed_count=confirmed_count,
            required_count=required_count,
            counts=counts,
        )
        missing = []
        if not ready:
            missing.append(StructuringJourneyService._missing_message(block_key, key, required_count, confirmed_count))

        return {
            "key": key,
            "label": label,
            "criticality": criticality,
            "status": status,
            "ready": ready,
            "maturity_pct": maturity_pct,
            "confirmed_count": confirmed_count,
            "required_count": required_count,
            "draft_count": int(counts.get("draft", 0)),
            "pending_count": int(counts.get("pending", 0)),
            "rejected_count": int(counts.get("rejected", 0)),
            "backlog_open": int(counts.get("draft", 0) + counts.get("pending", 0)),
            "evidence": evidence,
            "missing_to_ready": missing,
        }

    @staticmethod
    def _canonical_evidence(
        *,
        block_key: str,
        key: str,
        identity: dict[str, Any],
        process_areas: list[dict[str, Any]],
        macro_processes: list[dict[str, Any]],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        bpmn_diagrams: list[dict[str, Any]],
        routines: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
        execution_contracts: list[dict[str, Any]],
        growth_plans: list[dict[str, Any]],
        plan_section_statuses: list[dict[str, Any]],
        indicators: list[dict[str, Any]],
        indicator_data: list[dict[str, Any]],
        indicator_goals: list[dict[str, Any]],
        indicator_links: list[dict[str, Any]],
        line_of_sight: list[dict[str, Any]],
        incentive_rule_sets: list[dict[str, Any]],
        incentive_governability: list[dict[str, Any]],
    ) -> tuple[int, int, dict[str, Any]]:
        if block_key == "identity":
            fields = StructuringJourneyService.IDENTITY_SUBBLOCK_FIELDS[key]
            present = any(StructuringJourneyService._has_identity_value(identity.get(field)) for field in fields)
            return 1, int(present), {"fields": list(fields)}

        process_count = len(processes)
        if block_key == "processes":
            if key == "architecture":
                owner_covered = StructuringJourneyService._covered_processes_for_profile_key("process_owner", profiles, processes)
                checks = [
                    bool(process_areas),
                    bool(macro_processes),
                    bool(processes),
                    bool(process_count and len(owner_covered) >= process_count),
                ]
                return len(checks), sum(int(item) for item in checks), {
                    "areas_count": len(process_areas),
                    "macroprocesses_count": len(macro_processes),
                    "process_count": process_count,
                    "processes_with_owner": len(owner_covered),
                }
            if key == "modeling":
                modeled = StructuringJourneyService._covered_processes_for_modeling_key(
                    "flow",
                    processes=processes,
                    profiles=profiles,
                    bpmn_diagrams=bpmn_diagrams,
                    routines=routines,
                    process_steps=process_steps,
                    execution_contracts=execution_contracts,
                )
                pops = StructuringJourneyService._covered_processes_for_modeling_key(
                    "pops",
                    processes=processes,
                    profiles=profiles,
                    bpmn_diagrams=bpmn_diagrams,
                    routines=routines,
                    process_steps=process_steps,
                    execution_contracts=execution_contracts,
                )
                covered = modeled.intersection(pops) if pops else modeled
                return process_count, len(covered), {"process_count": process_count, "covered_process_ids": sorted(covered)}
            if key == "implementation":
                routine_process_ids = {int(item["process_id"]) for item in routines if item.get("process_id") is not None}
                contract_process_ids = {int(item["process_id"]) for item in execution_contracts if item.get("process_id") is not None}
                covered = routine_process_ids.union(contract_process_ids)
                return process_count, len(covered), {"process_count": process_count, "covered_process_ids": sorted(covered)}
            if key == "stabilization":
                indicator_process_ids = StructuringJourneyService._process_ids_with_indicators(profiles, processes, indicators, indicator_links)
                measured_indicator_ids = {int(item["indicator_id"]) for item in indicator_data if item.get("indicator_id") is not None}
                covered = {
                    process_id
                    for process_id in indicator_process_ids
                    if StructuringJourneyService._process_has_measured_indicator(process_id, indicators, indicator_links, measured_indicator_ids)
                }
                if not covered:
                    covered = indicator_process_ids
                return process_count, len(covered), {"process_count": process_count, "covered_process_ids": sorted(covered)}
            if key == "audit":
                return process_count, 0, {"process_count": process_count, "note": "Entrada no rol de auditoria interna ainda exige evidência específica."}

        if block_key == "growth_plan":
            active_growth_plans = [item for item in growth_plans if str(item.get("status") or "").lower() in {"active", "completed", "done"}]
            any_growth_plan = bool(growth_plans)
            completed_sections = [item for item in plan_section_statuses if str(item.get("status") or "").lower() in {"completed", "done"}]
            strategic_refs = [
                identity.get("strategic_objectives"),
                identity.get("pillars"),
                identity.get("objectives_pillars"),
            ]
            if key == "structured":
                present = any_growth_plan or any(StructuringJourneyService._has_identity_value(item) for item in strategic_refs)
                return 1, int(present), {"growth_plans": len(growth_plans), "completed_sections": len(completed_sections)}
            if key == "connected":
                present = bool(indicator_links or line_of_sight or completed_sections)
                return 1, int(present), {"indicator_links": len(indicator_links), "line_of_sight": len(line_of_sight)}
            if key == "deployed":
                linked_indicators = [item for item in indicators if item.get("project_id") or item.get("process_id") or item.get("okr_reference")]
                present = bool(linked_indicators or active_growth_plans)
                return 1, int(present), {"linked_indicators": len(linked_indicators), "active_growth_plans": len(active_growth_plans)}
            if key == "linked_to_management":
                present = bool(indicators and (indicator_data or indicator_goals or line_of_sight))
                return 1, int(present), {"indicators": len(indicators), "measurements": len(indicator_data), "goals": len(indicator_goals)}

        if block_key == "strategic_management":
            strategic_indicators = [item for item in indicators if str(item.get("source_scope") or "").lower() == "company" or item.get("okr_reference")]
            if key == "indicators":
                return 1, int(bool(indicators)), {"indicators": len(indicators), "strategic_indicators": len(strategic_indicators)}
            if key == "cycles":
                present = bool(indicator_data or indicator_goals)
                return 1, int(present), {"measurements": len(indicator_data), "goals": len(indicator_goals)}
            if key == "incentives":
                present = bool(incentive_rule_sets or incentive_governability)
                return 1, int(present), {"rule_sets": len(incentive_rule_sets), "governability_links": len(incentive_governability)}
            if key == "connection_web":
                present = bool(indicator_links or line_of_sight)
                return 1, int(present), {"indicator_links": len(indicator_links), "line_of_sight": len(line_of_sight)}

        return 1, 0, {}

    @staticmethod
    def _covered_processes_for_profile_key(
        key: str,
        profiles: list[dict[str, Any]],
        processes: list[dict[str, Any]],
    ) -> set[int]:
        fields = StructuringJourneyService.PROCESS_PROFILE_FIELDS.get(key, ())
        profiles_by_process = {
            int(profile["process_id"]): profile
            for profile in profiles
            if profile.get("process_id") is not None
        }
        covered: set[int] = set()
        for process in processes:
            process_id = int(process["id"])
            profile = profiles_by_process.get(process_id, {})
            if key == "process_owner":
                if StructuringJourneyService._truthy(process.get("responsible")) or process.get("owner_employee_id"):
                    covered.add(process_id)
                    continue
            if any(StructuringJourneyService._has_identity_value(profile.get(field)) for field in fields):
                covered.add(process_id)
        return covered

    @staticmethod
    def _covered_processes_for_modeling_key(
        key: str,
        *,
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        bpmn_diagrams: list[dict[str, Any]],
        routines: list[dict[str, Any]],
        process_steps: list[dict[str, Any]],
        execution_contracts: list[dict[str, Any]],
    ) -> set[int]:
        process_ids = {int(item["id"]) for item in processes if item.get("id") is not None}
        diagrams_by_process: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for diagram in bpmn_diagrams:
            if diagram.get("process_id") is not None:
                diagrams_by_process[int(diagram["process_id"])].append(diagram)
        routines_by_process: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for routine in routines:
            if routine.get("process_id") is not None:
                routines_by_process[int(routine["process_id"])].append(routine)
        routine_ids_with_steps = {int(step["routine_id"]) for step in process_steps if step.get("routine_id") is not None}
        profile_process_ids = StructuringJourneyService._covered_processes_for_profile_key("process_indicators", profiles, processes)

        covered: set[int] = set()
        for process_id in process_ids:
            diagrams = diagrams_by_process.get(process_id, [])
            xml_text = "\n".join(str(diagram.get("bpmn_xml") or "") for diagram in diagrams)
            if key == "flow":
                if diagrams or StructuringJourneyService._truthy(next((p.get("flow_mermaid") for p in processes if int(p["id"]) == process_id), None)):
                    covered.add(process_id)
            elif key == "lanes":
                if re.search(r"lane(Set)?\b|participant\b", xml_text, flags=re.IGNORECASE):
                    covered.add(process_id)
            elif key == "gateways":
                if re.search(r"gateway\b|exclusiveGateway|parallelGateway|inclusiveGateway", xml_text, flags=re.IGNORECASE):
                    covered.add(process_id)
            elif key == "pops":
                if any(int(routine.get("id") or 0) in routine_ids_with_steps for routine in routines_by_process.get(process_id, [])):
                    covered.add(process_id)
            elif key == "contracts_automation":
                if any(int(contract.get("process_id") or 0) == process_id for contract in execution_contracts):
                    covered.add(process_id)
            elif key == "flow_metrics":
                if process_id in profile_process_ids:
                    covered.add(process_id)
        return covered

    @staticmethod
    def _process_ids_with_indicators(
        profiles: list[dict[str, Any]],
        processes: list[dict[str, Any]],
        indicators: list[dict[str, Any]],
        indicator_links: list[dict[str, Any]],
    ) -> set[int]:
        covered = StructuringJourneyService._covered_processes_for_profile_key("process_indicators", profiles, processes)
        for indicator in indicators:
            if indicator.get("process_id") is not None:
                covered.add(int(indicator["process_id"]))
        for link in indicator_links:
            if str(link.get("target_type") or "").lower() == "process" and link.get("target_ref") is not None:
                try:
                    covered.add(int(link["target_ref"]))
                except (TypeError, ValueError):
                    continue
        return covered

    @staticmethod
    def _process_has_measured_indicator(
        process_id: int,
        indicators: list[dict[str, Any]],
        indicator_links: list[dict[str, Any]],
        measured_indicator_ids: set[int],
    ) -> bool:
        linked_indicator_ids = {
            int(item["id"])
            for item in indicators
            if item.get("id") is not None and item.get("process_id") is not None and int(item["process_id"]) == process_id
        }
        for link in indicator_links:
            if str(link.get("target_type") or "").lower() != "process":
                continue
            try:
                if int(link.get("target_ref")) == process_id and link.get("indicator_id") is not None:
                    linked_indicator_ids.add(int(link["indicator_id"]))
            except (TypeError, ValueError):
                continue
        return bool(linked_indicator_ids.intersection(measured_indicator_ids))

    @staticmethod
    def _maturation_counts(block_key: str, subblock_key: str, maturation_items: Iterable[dict[str, Any]]) -> Counter:
        counts: Counter = Counter()
        for item in maturation_items:
            if StructuringJourneyService._maturation_item_matches(block_key, subblock_key, item):
                counts[str(item.get("status") or "pending")] += 1
        return counts

    @staticmethod
    def _maturation_item_matches(block_key: str, subblock_key: str, item: dict[str, Any]) -> bool:
        payload = dict(item.get("payload") or item.get("payload_json") or {})
        item_block = str(item.get("block_type") or "").strip()

        if block_key == "identity":
            if item_block != "identity":
                return False
            fields = set(StructuringJourneyService.IDENTITY_SUBBLOCK_FIELDS[subblock_key])
            identity_field = str(payload.get("identity_field") or payload.get("field") or "").strip()
            if identity_field in fields:
                return True
            return bool(fields.intersection(payload.keys()))

        if block_key == "processes":
            if item_block not in {"process_profile", "process_modeling", "processes"}:
                return False
            mapping = {
                "architecture": {"areas", "macroprocesses", "processes", "process_owner", "owner", "owner_employee_id"},
                "modeling": {"flow", "bpmn_xml", "activities", "sequence", "pops", "procedures", "steps"},
                "implementation": {"implementation", "training", "project_id", "execution_contracts", "contracts"},
                "stabilization": {"stabilization", "cycles", "indicators", "control_ranges"},
                "audit": {"audit", "audit_periodicity", "internal_audit", "checklist"},
            }
            return bool(mapping.get(subblock_key, set()).intersection(payload.keys()))

        if block_key == "process_architecture":
            if item_block != "process_profile":
                return False
            fields = set(StructuringJourneyService.PROCESS_PROFILE_FIELDS.get(subblock_key, ()))
            return bool(fields.intersection(payload.keys()))

        if block_key == "modeling":
            if item_block not in {"process_profile", "process_modeling"}:
                return False
            mapping = {
                "flow": {"flow", "bpmn_xml", "activities", "sequence"},
                "lanes": {"lanes", "executors", "swimlanes"},
                "gateways": {"gateways", "decisions"},
                "pops": {"pops", "procedures", "steps"},
                "contracts_automation": {"contracts", "automation", "execution_contracts"},
                "flow_metrics": {"flow_metrics", "indicators"},
            }
            return bool(mapping.get(subblock_key, set()).intersection(payload.keys()))

        if block_key == "growth_plan":
            if item_block not in {"growth_plan", "strategic_planning", "planning"}:
                return False
            mapping = {
                "structured": {"structured", "plan", "growth_plan", "objectives", "pillars"},
                "connected": {"connected", "links", "processes", "indicators", "projects"},
                "deployed": {"deployed", "desdobrado", "initiatives", "projects", "owners"},
                "linked_to_management": {"linked_to_management", "management", "cycles", "review"},
            }
            return bool(mapping.get(subblock_key, set()).intersection(payload.keys()))

        if block_key == "strategic_management":
            if item_block not in {"strategic_management", "management", "indicators"}:
                return False
            mapping = {
                "indicators": {"indicators", "kpis", "metrics"},
                "cycles": {"cycles", "meetings", "reviews", "cadence"},
                "incentives": {"incentives", "rule_sets", "governability"},
                "connection_web": {"connection_web", "teia", "line_of_sight", "links"},
            }
            return bool(mapping.get(subblock_key, set()).intersection(payload.keys()))

        return False

    @staticmethod
    def _subblock_status(*, ready: bool, confirmed_count: int, required_count: int, counts: Counter) -> str:
        if ready:
            return "confirmed"
        if confirmed_count > 0 and required_count > confirmed_count:
            return "partial"
        if counts.get("pending", 0) or counts.get("draft", 0):
            return "pending"
        if counts.get("rejected", 0):
            return "rejected"
        return "gap"

    @staticmethod
    def _missing_message(block_key: str, key: str, required_count: int, confirmed_count: int) -> str:
        if required_count <= 0:
            return "Cadastre a base anterior necessária para calcular este sub-bloco."
        missing = max(required_count - confirmed_count, 0)
        if block_key in {"processes", "process_architecture", "modeling"} and required_count > 1:
            return f"Faltam {missing} de {required_count} processos para este sub-bloco."
        return "Confirmar este sub-bloco para avançar."

    @staticmethod
    def _with_org_chart_evidence(company_id: int, identity: dict[str, Any]) -> dict[str, Any]:
        roles_total = Role.query.filter_by(company_id=company_id).count()
        active_employees_total = Employee.query.filter_by(company_id=company_id, status="active").count()
        employees_with_role = (
            Employee.query.filter(
                Employee.company_id == company_id,
                Employee.status == "active",
                Employee.role_id.isnot(None),
            ).count()
        )
        has_role_hierarchy = (
            Role.query.filter(
                Role.company_id == company_id,
                Role.parent_role_id.isnot(None),
            ).count()
            > 0
        )
        identity["_org_chart_present"] = bool(
            roles_total
            and (
                active_employees_total == 0
                or employees_with_role == active_employees_total
                or has_role_hierarchy
            )
        )
        identity["_org_chart_evidence"] = {
            "roles_total": int(roles_total or 0),
            "active_employees_total": int(active_employees_total or 0),
            "employees_with_role": int(employees_with_role or 0),
            "has_role_hierarchy": has_role_hierarchy,
        }
        return identity

    @staticmethod
    def _has_identity_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    @staticmethod
    def _truthy(value: Any) -> bool:
        return StructuringJourneyService._has_identity_value(value)

    @staticmethod
    def _pct(numerator: int, denominator: int) -> int | None:
        if denominator <= 0:
            return 0
        return int(round((float(numerator) / float(denominator)) * 100))

    @staticmethod
    def _average(values: list[int | None]) -> int:
        usable = [int(value) for value in values if value is not None]
        if not usable:
            return 0
        return int(round(sum(usable) / len(usable)))

    @staticmethod
    def _process_payload(row: Process) -> dict[str, Any]:
        return {
            "id": row.id,
            "company_id": row.company_id,
            "macro_id": row.macro_id,
            "code": row.code,
            "name": row.name,
            "responsible": row.responsible,
            "owner_employee_id": row.owner_employee_id,
            "structuring_level": row.structuring_level,
            "flow_mermaid": row.flow_mermaid,
        }

    @staticmethod
    def _area_payload(row: ProcessArea) -> dict[str, Any]:
        return {"id": row.id, "company_id": row.company_id, "name": row.name, "code": row.code}

    @staticmethod
    def _macro_payload(row: MacroProcess) -> dict[str, Any]:
        return {"id": row.id, "company_id": row.company_id, "area_id": row.area_id, "name": row.name, "code": row.code}

    @staticmethod
    def _bpmn_payload(row: ProcessBpmnDiagram) -> dict[str, Any]:
        return {
            "id": row.id,
            "company_id": row.company_id,
            "process_id": row.process_id,
            "status": row.status,
            "name": row.name,
            "bpmn_xml": row.bpmn_xml,
            "metadata": row.metadata_json or {},
        }

    @staticmethod
    def _routine_payload(row: ProcessRoutine) -> dict[str, Any]:
        return {
            "id": row.id,
            "company_id": row.company_id,
            "process_id": row.process_id,
            "name": row.name,
            "bpmn_element_id": row.bpmn_element_id,
        }

    @staticmethod
    def _step_payload(row: ProcessStep) -> dict[str, Any]:
        return {"id": row.id, "routine_id": row.routine_id, "name": row.name}
