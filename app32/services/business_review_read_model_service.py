from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from models import (
    AuditChecklist,
    AuditSchedule,
    BusinessReviewRecord,
    Company,
    Employee,
    IncentiveGovernabilityMatrix,
    IncentiveRule,
    IncentiveRuleSet,
    Indicator,
    IndicatorData,
    IndicatorEntityLink,
    IndicatorGoal,
    IndicatorLineOfSight,
    KeyResult,
    KeyResultArea,
    MacroProcess,
    Meeting,
    OKRArea,
    OKRGlobal,
    OrganizationalIdentity,
    Plan,
    PlanDriver,
    PlanSectionStatus,
    Process,
    ProcessActivityExecutionContract,
    ProcessArea,
    ProcessBpmnDiagram,
    ProcessRoutine,
    ProcessStep,
    ProcessStrategicAlignmentLink,
    Project,
    Role,
    StructuralLearningLink,
    StrategyMaturationItem,
    UrgentNeedOverlay,
    db,
)
from services.urgent_business_review_common import require_company


class BusinessReviewReadModelService:
    """Read model tenant-safe para o cockpit consultivo Versus.

    Não altera estado. Consolida Necessidades Urgentes, Business Reviews e
    aprendizados estruturais para apoiar a condução metodológica.
    """

    READ_MODEL = "consultive.business_review_cockpit"
    VERSION = "v1"

    STRUCTURAL_FRONTS: list[dict[str, Any]] = [
        {
            "key": "identity",
            "title": "Identidade Organizacional",
            "status": "A estruturar",
            "maturity": "56%",
            "tags": [
                {"label": "1 - Missão · OK · 100%", "status": "ok"},
                {"label": "2 - Visão · Parcial · 60%", "status": "partial"},
                {"label": "3 - Valores · Revisar · 80%", "status": "review"},
                {"label": "4 - Posicionamento · Pendente · 0%", "status": "pending"},
                {"label": "5 - Organograma · Parcial · 40%", "status": "partial"},
            ],
        },
        {
            "key": "processes",
            "title": "Processos",
            "status": "A estruturar",
            "maturity": "47%",
            "tags": [
                {"label": "1 - Arquitetura · OK · 100%", "status": "ok"},
                {"label": "2 - Modelagem · Parcial · 55%", "status": "partial"},
                {"label": "3 - Implantação · Em projeto · 30%", "status": "partial"},
                {"label": "4 - Estabilização · 1/3 ciclos", "status": "review"},
                {"label": "5 - Auditoria · Pendente · 0%", "status": "pending"},
            ],
        },
        {
            "key": "growth_plan",
            "title": "Planejamento Estratégico",
            "status": "A estruturar",
            "maturity": "52%",
            "tags": [
                {"label": "1 - Estruturado · OK · 100%", "status": "ok"},
                {"label": "2 - Conectado · Parcial · 60%", "status": "partial"},
                {"label": "3 - Desdobrado · Parcial · 50%", "status": "partial"},
                {"label": "4 - Vinculado à gestão · Pendente · 0%", "status": "pending"},
            ],
        },
        {
            "key": "strategic_management",
            "title": "Gerenciamento Estratégico",
            "status": "A estruturar",
            "maturity": "40%",
            "tags": [
                {"label": "1 - Indicadores · Parcial · 60%", "status": "partial"},
                {"label": "2 - Ciclos · OK · 100%", "status": "ok"},
                {"label": "3 - Incentivos · Revisar · 40%", "status": "review"},
                {"label": "4 - Teia · Pendente · 0%", "status": "pending"},
            ],
        },
    ]

    @staticmethod
    def get_cockpit(company_id: int, *, limit: int = 20) -> dict[str, Any]:
        require_company(company_id)
        safe_limit = max(1, min(int(limit or 20), 100))

        warnings: list[str] = []
        urgent_needs = BusinessReviewReadModelService._safe_all(
            UrgentNeedOverlay,
            company_id=company_id,
            warnings=warnings,
            label="urgent_need_overlays",
        )
        reviews = BusinessReviewReadModelService._safe_all(
            BusinessReviewRecord,
            company_id=company_id,
            warnings=warnings,
            label="business_review_records",
        )
        learnings = BusinessReviewReadModelService._safe_all(
            StructuralLearningLink,
            company_id=company_id,
            warnings=warnings,
            label="structural_learning_links",
        )

        open_urgent_needs = [
            item
            for item in urgent_needs
            if item.status not in {"closed", "cancelled"}
        ]
        pending_reviews = [
            item
            for item in reviews
            if item.status not in {"rejected"}
        ]
        pending_learnings = [
            item
            for item in learnings
            if item.action_decision in {"recommended", "approved"}
            and not item.created_project_id
            and not item.created_task_id
        ]

        return {
            "company_id": company_id,
            "read_model": BusinessReviewReadModelService.READ_MODEL,
            "version": BusinessReviewReadModelService.VERSION,
            "warnings": warnings,
            "summary": {
                "urgent_needs_total": len(urgent_needs),
                "urgent_needs_open": len(open_urgent_needs),
                "critical_urgent_needs_open": sum(
                    1 for item in open_urgent_needs if item.urgency_level == "critical"
                ),
                "business_reviews_total": len(reviews),
                "business_reviews_pending_decision": len(pending_reviews),
                "structural_learning_total": len(learnings),
                "structural_learning_pending_action": len(pending_learnings),
                "financial_exposure": BusinessReviewReadModelService._financial_summary(reviews),
            },
            "structural_enterprise": {
                "maturity_track": BusinessReviewReadModelService._structuring_maturity_track_payload(
                    company_id=company_id,
                    warnings=warnings,
                ),
                "fronts": BusinessReviewReadModelService._structural_fronts_payload(),
            },
            "urgent_needs": {
                "by_status": BusinessReviewReadModelService._count_by(urgent_needs, "status"),
                "by_urgency": BusinessReviewReadModelService._count_by(urgent_needs, "urgency_level"),
                "by_criticality": BusinessReviewReadModelService._count_by(urgent_needs, "criticality_level"),
                "open_items": [
                    BusinessReviewReadModelService._urgent_need_payload(item)
                    for item in open_urgent_needs[:safe_limit]
                ],
            },
            "business_reviews": {
                "by_status": BusinessReviewReadModelService._count_by(reviews, "status"),
                "by_type": BusinessReviewReadModelService._count_by(reviews, "review_type"),
                "pending_decisions": [
                    BusinessReviewReadModelService._business_review_payload(item)
                    for item in pending_reviews[:safe_limit]
                ],
                "risk_accepted": [
                    item.to_dict()
                    for item in reviews
                    if bool(item.risk_acceptance_decision)
                ][:safe_limit],
            },
            "structural_learning": {
                "by_type": BusinessReviewReadModelService._count_by(learnings, "learning_type"),
                "by_action": BusinessReviewReadModelService._count_by(learnings, "action_decision"),
                "pending_actions": [item.to_dict() for item in pending_learnings[:safe_limit]],
            },
            "next_focus": BusinessReviewReadModelService._next_focus(
                open_urgent_needs=open_urgent_needs,
                pending_reviews=pending_reviews,
                pending_learnings=pending_learnings,
            ),
        }

    @staticmethod
    def get_structural_front_analysis(company_id: int, front_key: str) -> dict[str, Any]:
        """Diagnóstico determinístico inicial de uma frente do cockpit.

        A primeira entrega não executa IA generativa. Ela devolve um envelope
        agentic compatível com a SPEC usando o read model atual e critérios
        metodológicos conservadores.
        """
        require_company(company_id)
        front = BusinessReviewReadModelService._front_by_key(front_key)
        if front is None:
            raise ValueError("Frente estrutural inválida para análise assistida.")

        if front["key"] == "identity":
            return BusinessReviewReadModelService._identity_front_analysis(company_id=company_id, front=front)
        if front["key"] == "processes":
            return BusinessReviewReadModelService._processes_front_analysis(company_id=company_id, front=front)
        if front["key"] == "growth_plan":
            return BusinessReviewReadModelService._growth_plan_front_analysis(company_id=company_id, front=front)
        if front["key"] == "strategic_management":
            return BusinessReviewReadModelService._strategic_management_front_analysis(company_id=company_id, front=front)

        score = BusinessReviewReadModelService._maturity_score(front.get("maturity"))
        tags = front.get("tags", [])
        gaps = BusinessReviewReadModelService._front_gaps(front["key"], tags)
        recommendations = BusinessReviewReadModelService._front_recommendations(front["key"])
        engineering_gaps = BusinessReviewReadModelService._front_engineering_gaps(front["key"])

        return {
            "front": front["key"],
            "action": "analyze_front",
            "company_id": company_id,
            "summary": BusinessReviewReadModelService._front_summary(front, gaps),
            "maturity": {
                "status": BusinessReviewReadModelService._maturity_status(score),
                "score": score,
                "basis": "Leitura determinística inicial baseada nos microstatus da frente no Cockpit.",
            },
            "internal_evidence": [
                {
                    "type": "structural_microstatus",
                    "id": index + 1,
                    "label": tag.get("label"),
                    "finding": f"Status metodológico atual: {tag.get('status') or 'não classificado'}.",
                }
                for index, tag in enumerate(tags)
            ],
            "gaps": gaps,
            "recommendations": recommendations,
            "external_benchmarks": [],
            "engineering_gaps": engineering_gaps,
            "human_gate_required": True,
            "suggested_next_action": "open_maturation_plan",
            "state": "draft",
        }


    @staticmethod
    def _safe_all(model: Any, *, company_id: int, warnings: list[str], label: str) -> list[Any]:
        try:
            return (
                model.query.filter_by(company_id=company_id)
                .order_by(model.updated_at.desc(), model.id.desc())
                .limit(500)
                .all()
            )
        except SQLAlchemyError as exc:
            db.session.rollback()
            warnings.append(f"{label}: {exc.__class__.__name__}")
        return []

    @staticmethod
    def _safe_count(query: Any, *, warnings: list[str], label: str) -> int:
        try:
            return int(query.count())
        except SQLAlchemyError as exc:
            db.session.rollback()
            warnings.append(f"{label}: {exc.__class__.__name__}")
            return 0

    @staticmethod
    def _safe_first(query: Any, *, warnings: list[str], label: str) -> Any | None:
        try:
            return query.first()
        except SQLAlchemyError as exc:
            db.session.rollback()
            warnings.append(f"{label}: {exc.__class__.__name__}")
            return None

    @staticmethod
    def _identity_front_analysis(company_id: int, front: dict[str, Any]) -> dict[str, Any]:
        """Análise assistida da Identidade ancorada em MVV, posicionamento e organograma."""
        warnings: list[str] = []
        company = BusinessReviewReadModelService._safe_first(
            Company.query.filter(Company.id == company_id),
            warnings=warnings,
            label="company",
        )
        identity = BusinessReviewReadModelService._safe_first(
            OrganizationalIdentity.query.filter(OrganizationalIdentity.company_id == company_id),
            warnings=warnings,
            label="organizational_identity",
        )

        identity_payload = identity.to_dict() if identity else {}
        mission_present = BusinessReviewReadModelService._filled(
            identity_payload.get("mission") or getattr(company, "mission", None)
        )
        vision_present = BusinessReviewReadModelService._filled(
            identity_payload.get("vision") or getattr(company, "vision", None)
        )
        values_present = BusinessReviewReadModelService._filled_list(
            identity_payload.get("values")
        ) or BusinessReviewReadModelService._filled(getattr(company, "values", None))
        positioning_present = any(
            [
                BusinessReviewReadModelService._filled_list(identity_payload.get("value_propositions")),
                BusinessReviewReadModelService._filled_list(identity_payload.get("differentials")),
                BusinessReviewReadModelService._filled_list(identity_payload.get("segments_icp")),
                BusinessReviewReadModelService._filled(getattr(company, "description", None)),
                BusinessReviewReadModelService._filled(getattr(company, "segment", None)),
            ]
        )

        roles_total = BusinessReviewReadModelService._safe_count(
            Role.query.filter(Role.company_id == company_id),
            warnings=warnings,
            label="roles",
        )
        root_roles_total = BusinessReviewReadModelService._safe_count(
            Role.query.filter(Role.company_id == company_id, Role.parent_role_id.is_(None)),
            warnings=warnings,
            label="root_roles",
        )
        employees_total = BusinessReviewReadModelService._safe_count(
            Employee.query.filter(Employee.company_id == company_id),
            warnings=warnings,
            label="employees",
        )
        active_employees_total = BusinessReviewReadModelService._safe_count(
            Employee.query.filter(
                Employee.company_id == company_id,
                or_(Employee.status.is_(None), Employee.status == "", Employee.status.in_(["active", "ativo"])),
            ),
            warnings=warnings,
            label="active_employees",
        )
        employees_without_role = BusinessReviewReadModelService._safe_count(
            Employee.query.filter(
                Employee.company_id == company_id,
                or_(Employee.status.is_(None), Employee.status == "", Employee.status.in_(["active", "ativo"])),
                Employee.role_id.is_(None),
            ),
            warnings=warnings,
            label="employees_without_role",
        )
        maturation_pending_total = BusinessReviewReadModelService._safe_count(
            StrategyMaturationItem.query.filter(
                StrategyMaturationItem.company_id == company_id,
                StrategyMaturationItem.block_type == "identity",
                StrategyMaturationItem.status.in_(["draft", "pending"]),
            ),
            warnings=warnings,
            label="strategy_maturation_identity",
        )

        organogram_present = roles_total > 0 and (active_employees_total == 0 or employees_without_role < active_employees_total)
        identity_checks = {
            "mission": mission_present,
            "vision": vision_present,
            "values": values_present,
            "positioning": positioning_present,
            "organogram": organogram_present,
        }
        score = BusinessReviewReadModelService._pct(sum(1 for item in identity_checks.values() if item), len(identity_checks))
        evidence = [
            {
                "type": "identity",
                "label": "Missão",
                "finding": "Registrada." if mission_present else "Não encontrada no cadastro estruturado/legado.",
            },
            {
                "type": "identity",
                "label": "Visão",
                "finding": "Registrada." if vision_present else "Não encontrada no cadastro estruturado/legado.",
            },
            {
                "type": "identity",
                "label": "Valores",
                "finding": "Registrados." if values_present else "Não encontrados no cadastro estruturado/legado.",
            },
            {
                "type": "positioning",
                "label": "Posicionamento",
                "finding": (
                    "Há evidência em proposta de valor, diferenciais, ICP, descrição ou segmento."
                    if positioning_present
                    else "Sem evidência suficiente de posicionamento."
                ),
            },
            {
                "type": "organogram",
                "label": "Organograma",
                "finding": (
                    f"{roles_total} cargo(s), {root_roles_total} raiz(es), "
                    f"{active_employees_total} colaborador(es) ativo(s), {employees_without_role} sem cargo."
                ),
            },
            {
                "type": "maturation",
                "label": "Maturação assistida",
                "finding": f"{maturation_pending_total} item(ns) de identidade em draft/pendente.",
            },
        ]
        gaps = BusinessReviewReadModelService._identity_front_gaps(
            identity_checks=identity_checks,
            roles_total=roles_total,
            employees_without_role=employees_without_role,
            maturation_pending_total=maturation_pending_total,
        )
        return {
            "front": front["key"],
            "action": "analyze_front",
            "company_id": company_id,
            "summary": (
                "Identidade Organizacional analisada com base em MVV, posicionamento, "
                "estrutura de cargos, colaboradores e itens de maturação N1."
            ),
            "maturity": {
                "status": BusinessReviewReadModelService._maturity_status(score),
                "score": score,
                "basis": "Missão, visão, valores, posicionamento e organograma no APP32.",
            },
            "internal_evidence": evidence,
            "gaps": gaps,
            "recommendations": BusinessReviewReadModelService._identity_front_recommendations(
                identity_checks=identity_checks,
                roles_total=roles_total,
                employees_without_role=employees_without_role,
                maturation_pending_total=maturation_pending_total,
            ),
            "external_benchmarks": [],
            "engineering_gaps": [
                {
                    "type": "read_model_gap",
                    "severity": "medium",
                    "description": (
                        "Consolidar Company.legacy MVV e OrganizationalIdentity em contrato único, "
                        "evitando dupla fonte para missão, visão e valores."
                    ),
                },
                {
                    "type": "agentic_gap",
                    "severity": "medium",
                    "description": (
                        "Análise de coerência semântica, benchmark setorial e pesquisa externa profunda "
                        "ainda dependem do próximo passo agentic com gate humano."
                    ),
                },
            ],
            "warnings": warnings,
            "human_gate_required": True,
            "suggested_next_action": "open_maturation_plan",
            "state": "draft",
        }

    @staticmethod
    def _filled(value: Any) -> bool:
        return bool(str(value or "").strip())

    @staticmethod
    def _filled_list(value: Any) -> bool:
        if isinstance(value, list):
            return any(item for item in value)
        return False

    @staticmethod
    def _pct(present: int, total: int) -> int:
        if total <= 0:
            return 0
        return max(0, min(int(round((present / total) * 100)), 100))

    @staticmethod
    def _identity_front_gaps(
        *,
        identity_checks: dict[str, bool],
        roles_total: int,
        employees_without_role: int,
        maturation_pending_total: int,
    ) -> list[dict[str, str]]:
        labels = {
            "mission": "Missão",
            "vision": "Visão",
            "values": "Valores",
            "positioning": "Posicionamento",
            "organogram": "Organograma",
        }
        gaps: list[dict[str, str]] = [
            {
                "type": "identity",
                "severity": "high" if key in {"mission", "vision", "positioning"} else "medium",
                "description": f"{label} ainda não possui evidência suficiente no APP32.",
            }
            for key, label in labels.items()
            if not identity_checks.get(key)
        ]
        if roles_total and employees_without_role:
            gaps.append(
                {
                    "type": "organogram",
                    "severity": "medium",
                    "description": f"{employees_without_role} colaborador(es) ativo(s) ainda estão sem cargo no organograma.",
                }
            )
        if maturation_pending_total:
            gaps.append(
                {
                    "type": "maturation",
                    "severity": "medium",
                    "description": f"{maturation_pending_total} item(ns) de identidade aguardam validação/decisão.",
                }
            )
        if not gaps:
            gaps.append(
                {
                    "type": "methodological",
                    "severity": "low",
                    "description": "Identidade Organizacional sem gaps críticos no diagnóstico operacional inicial.",
                }
            )
        return gaps

    @staticmethod
    def _identity_front_recommendations(
        *,
        identity_checks: dict[str, bool],
        roles_total: int,
        employees_without_role: int,
        maturation_pending_total: int,
    ) -> list[dict[str, str]]:
        recommendations: list[str] = []
        if not identity_checks.get("mission") or not identity_checks.get("vision"):
            recommendations.append("Consolidar missão e visão em texto simples, validado pelo cliente e utilizável na gestão.")
        if not identity_checks.get("values"):
            recommendations.append("Definir valores em formato objetivo, observável e conectável a políticas/comportamentos.")
        if not identity_checks.get("positioning"):
            recommendations.append("Formalizar posicionamento com proposta de valor, diferenciais e público/segmento prioritário.")
        if not roles_total:
            recommendations.append("Criar a primeira versão do organograma com cargos, áreas e relações de reporte.")
        elif employees_without_role:
            recommendations.append("Associar colaboradores ativos aos cargos corretos para tornar o organograma operacional.")
        if maturation_pending_total:
            recommendations.append("Levar itens pendentes de identidade para gate humano do consultor e promover o que for aceito.")
        recommendations.append("Validar coerência entre identidade, processos e planejamento estratégico antes de marcar OK.")
        return [
            {"priority": f"P{min(index + 1, 3)}", "description": description, "target_object": "identity"}
            for index, description in enumerate(recommendations)
        ]

    @staticmethod
    def _growth_plan_front_analysis(company_id: int, front: dict[str, Any]) -> dict[str, Any]:
        """Análise assistida do Planejamento Estratégico focada em crescimento."""
        warnings: list[str] = []
        growth_plans_total = BusinessReviewReadModelService._safe_count(
            Plan.query.filter(Plan.company_id == company_id, Plan.mode == "growth"),
            warnings=warnings,
            label="growth_plans",
        )
        active_growth_plans_total = BusinessReviewReadModelService._safe_count(
            Plan.query.filter(Plan.company_id == company_id, Plan.mode == "growth", Plan.status == "active"),
            warnings=warnings,
            label="active_growth_plans",
        )
        plan_drivers_total = BusinessReviewReadModelService._safe_count(
            PlanDriver.query.join(Plan, Plan.id == PlanDriver.plan_id).filter(
                Plan.company_id == company_id,
                Plan.mode == "growth",
            ),
            warnings=warnings,
            label="plan_drivers",
        )
        completed_sections_total = BusinessReviewReadModelService._safe_count(
            PlanSectionStatus.query.join(Plan, Plan.id == PlanSectionStatus.plan_id).filter(
                Plan.company_id == company_id,
                Plan.mode == "growth",
                PlanSectionStatus.status == "completed",
            ),
            warnings=warnings,
            label="plan_section_status_completed",
        )
        okrs_global_total = BusinessReviewReadModelService._safe_count(
            OKRGlobal.query.filter(OKRGlobal.company_id == company_id),
            warnings=warnings,
            label="okrs_global",
        )
        okrs_area_total = BusinessReviewReadModelService._safe_count(
            OKRArea.query.filter(OKRArea.company_id == company_id),
            warnings=warnings,
            label="okrs_area",
        )
        key_results_global_total = BusinessReviewReadModelService._safe_count(
            KeyResult.query.join(OKRGlobal, OKRGlobal.id == KeyResult.okr_global_id).filter(
                OKRGlobal.company_id == company_id
            ),
            warnings=warnings,
            label="key_results_global",
        )
        key_results_area_total = BusinessReviewReadModelService._safe_count(
            KeyResultArea.query.join(OKRArea, OKRArea.id == KeyResultArea.okr_area_id).filter(
                OKRArea.company_id == company_id
            ),
            warnings=warnings,
            label="key_results_area",
        )
        area_okrs_linked_total = BusinessReviewReadModelService._safe_count(
            OKRArea.query.filter(
                OKRArea.company_id == company_id,
                OKRArea.linked_okr_ids.isnot(None),
            ),
            warnings=warnings,
            label="area_okrs_linked",
        )
        strategic_projects_total = BusinessReviewReadModelService._safe_count(
            Project.query.filter(
                Project.company_id == company_id,
                Project.is_deleted.is_(False),
                or_(Project.plan_id.isnot(None), Project.okr_links.isnot(None)),
            ),
            warnings=warnings,
            label="strategic_projects",
        )
        linked_processes_total = BusinessReviewReadModelService._safe_count(
            ProcessStrategicAlignmentLink.query.filter(
                ProcessStrategicAlignmentLink.company_id == company_id,
                ProcessStrategicAlignmentLink.target_ref_type.in_(["okr_global", "okr_area", "plan_driver"]),
            ),
            warnings=warnings,
            label="process_strategic_alignment_links",
        )
        maturation_pending_total = BusinessReviewReadModelService._safe_count(
            StrategyMaturationItem.query.filter(
                StrategyMaturationItem.company_id == company_id,
                StrategyMaturationItem.target_ref_type.in_(["okr_global", "okr_area", "plan_driver"]),
                StrategyMaturationItem.status.in_(["draft", "pending"]),
            ),
            warnings=warnings,
            label="strategy_maturation_growth_plan",
        )

        structured = active_growth_plans_total > 0 or growth_plans_total > 0
        connected = linked_processes_total > 0 or strategic_projects_total > 0
        unfolded = okrs_global_total > 0 and (okrs_area_total > 0 or key_results_global_total > 0)
        linked_to_management = strategic_projects_total > 0 and (key_results_global_total + key_results_area_total) > 0
        checks = {
            "structured": structured,
            "connected": connected,
            "unfolded": unfolded,
            "linked_to_management": linked_to_management,
        }
        score = BusinessReviewReadModelService._pct(sum(1 for item in checks.values() if item), len(checks))
        evidence = [
            {
                "type": "plan",
                "label": "Planejamento de crescimento",
                "finding": f"{growth_plans_total} plano(s), {active_growth_plans_total} ativo(s).",
            },
            {
                "type": "drivers",
                "label": "Direcionadores estratégicos",
                "finding": f"{plan_drivers_total} driver(s) e {completed_sections_total} seção(ões) concluída(s).",
            },
            {
                "type": "okr_global",
                "label": "OKRs globais",
                "finding": f"{okrs_global_total} OKR(s) global(is) e {key_results_global_total} KR(s).",
            },
            {
                "type": "okr_area",
                "label": "Desdobramento por área",
                "finding": f"{okrs_area_total} OKR(s) de área, {area_okrs_linked_total} vinculado(s) e {key_results_area_total} KR(s).",
            },
            {
                "type": "execution",
                "label": "Projetos vinculados",
                "finding": f"{strategic_projects_total} projeto(s) com plano ou OKR vinculado.",
            },
            {
                "type": "connection",
                "label": "Conexão com processos",
                "finding": f"{linked_processes_total} vínculo(s) processo -> estratégia.",
            },
            {
                "type": "maturation",
                "label": "Maturação assistida",
                "finding": f"{maturation_pending_total} item(ns) estratégicos em draft/pendente.",
            },
        ]
        gaps = BusinessReviewReadModelService._growth_plan_front_gaps(
            checks=checks,
            growth_plans_total=growth_plans_total,
            plan_drivers_total=plan_drivers_total,
            okrs_global_total=okrs_global_total,
            okrs_area_total=okrs_area_total,
            strategic_projects_total=strategic_projects_total,
            linked_processes_total=linked_processes_total,
            maturation_pending_total=maturation_pending_total,
        )
        return {
            "front": front["key"],
            "action": "analyze_front",
            "company_id": company_id,
            "summary": (
                "Planejamento Estratégico analisado pelo plano de crescimento, direcionadores, "
                "OKRs, KRs, projetos e vínculos com processos."
            ),
            "maturity": {
                "status": BusinessReviewReadModelService._maturity_status(score),
                "score": score,
                "basis": "Estruturado, conectado, desdobrado e vinculado ao Gerenciamento Estratégico.",
            },
            "internal_evidence": evidence,
            "gaps": gaps,
            "recommendations": BusinessReviewReadModelService._growth_plan_front_recommendations(
                checks=checks,
                growth_plans_total=growth_plans_total,
                plan_drivers_total=plan_drivers_total,
                okrs_global_total=okrs_global_total,
                okrs_area_total=okrs_area_total,
                strategic_projects_total=strategic_projects_total,
                linked_processes_total=linked_processes_total,
                maturation_pending_total=maturation_pending_total,
            ),
            "external_benchmarks": [],
            "engineering_gaps": [
                {
                    "type": "read_model_gap",
                    "severity": "medium",
                    "description": (
                        "Normalizar contrato entre planejamento estratégico, OKRs, projetos, processos "
                        "e gerenciamento estratégico para evitar leituras espalhadas."
                    ),
                },
                {
                    "type": "method_gap",
                    "severity": "medium",
                    "description": (
                        "A maturidade ainda mede existência e vínculos; falta medir qualidade estratégica, "
                        "coerência causal e efetividade por ciclos de gestão."
                    ),
                },
            ],
            "warnings": warnings,
            "human_gate_required": True,
            "suggested_next_action": "open_maturation_plan",
            "state": "draft",
        }

    @staticmethod
    def _growth_plan_front_gaps(
        *,
        checks: dict[str, bool],
        growth_plans_total: int,
        plan_drivers_total: int,
        okrs_global_total: int,
        okrs_area_total: int,
        strategic_projects_total: int,
        linked_processes_total: int,
        maturation_pending_total: int,
    ) -> list[dict[str, str]]:
        gaps: list[dict[str, str]] = []
        if not checks.get("structured"):
            gaps.append(
                {
                    "type": "planning",
                    "severity": "high",
                    "description": "Não há Planejamento Estratégico de crescimento estruturado para a empresa.",
                }
            )
        elif not plan_drivers_total:
            gaps.append(
                {
                    "type": "planning",
                    "severity": "medium",
                    "description": "Plano de crescimento existe, mas sem direcionadores estratégicos registrados.",
                }
            )
        if growth_plans_total and not okrs_global_total:
            gaps.append(
                {
                    "type": "okr",
                    "severity": "high",
                    "description": "Planejamento ainda não foi traduzido em OKRs globais.",
                }
            )
        if okrs_global_total and not okrs_area_total:
            gaps.append(
                {
                    "type": "unfolding",
                    "severity": "medium",
                    "description": "OKRs globais ainda não foram desdobrados para áreas.",
                }
            )
        if okrs_global_total and not strategic_projects_total:
            gaps.append(
                {
                    "type": "execution",
                    "severity": "medium",
                    "description": "Estratégia ainda não está suficientemente vinculada a projetos de execução.",
                }
            )
        if okrs_global_total and not linked_processes_total:
            gaps.append(
                {
                    "type": "connection",
                    "severity": "medium",
                    "description": "Estratégia ainda não possui vínculos suficientes com processos.",
                }
            )
        if maturation_pending_total:
            gaps.append(
                {
                    "type": "maturation",
                    "severity": "medium",
                    "description": f"{maturation_pending_total} item(ns) estratégicos aguardam validação/decisão.",
                }
            )
        if not gaps:
            gaps.append(
                {
                    "type": "methodological",
                    "severity": "low",
                    "description": "Planejamento Estratégico sem gaps críticos no diagnóstico operacional inicial.",
                }
            )
        return gaps

    @staticmethod
    def _growth_plan_front_recommendations(
        *,
        checks: dict[str, bool],
        growth_plans_total: int,
        plan_drivers_total: int,
        okrs_global_total: int,
        okrs_area_total: int,
        strategic_projects_total: int,
        linked_processes_total: int,
        maturation_pending_total: int,
    ) -> list[dict[str, str]]:
        recommendations: list[str] = []
        if not checks.get("structured"):
            recommendations.append("Criar ou ativar o Planejamento Estratégico de crescimento antes de avaliar maturidade.")
        elif not plan_drivers_total:
            recommendations.append("Registrar direcionadores, oportunidades e ameaças que justificam o plano.")
        if growth_plans_total and not okrs_global_total:
            recommendations.append("Traduzir o planejamento em OKRs globais com responsáveis, prazos e KRs.")
        if okrs_global_total and not okrs_area_total:
            recommendations.append("Desdobrar OKRs globais para áreas responsáveis pela execução.")
        if okrs_global_total and not strategic_projects_total:
            recommendations.append("Vincular projetos/programas aos OKRs para transformar estratégia em execução.")
        if okrs_global_total and not linked_processes_total:
            recommendations.append("Conectar OKRs e direcionadores aos processos que materializam a estratégia.")
        if maturation_pending_total:
            recommendations.append("Levar itens estratégicos pendentes para gate humano do consultor.")
        recommendations.append("Validar se o planejamento está ligado ao Gerenciamento Estratégico antes de marcar OK.")
        return [
            {"priority": f"P{min(index + 1, 3)}", "description": description, "target_object": "growth_plan"}
            for index, description in enumerate(recommendations)
        ]

    @staticmethod
    def _strategic_management_front_analysis(company_id: int, front: dict[str, Any]) -> dict[str, Any]:
        """Análise assistida do Gerenciamento Estratégico."""
        warnings: list[str] = []
        active_indicators_total = BusinessReviewReadModelService._safe_count(
            Indicator.query.filter(Indicator.company_id == company_id, Indicator.is_active.is_(True)),
            warnings=warnings,
            label="active_indicators",
        )
        indicators_with_responsible_total = BusinessReviewReadModelService._safe_count(
            Indicator.query.filter(
                Indicator.company_id == company_id,
                Indicator.is_active.is_(True),
                Indicator.responsible_id.isnot(None),
            ),
            warnings=warnings,
            label="indicators_with_responsible",
        )
        indicators_with_goals_total = BusinessReviewReadModelService._safe_count(
            Indicator.query.filter(
                Indicator.company_id == company_id,
                Indicator.is_active.is_(True),
                Indicator.id.in_(
                    db.session.query(IndicatorGoal.indicator_id).filter(
                        IndicatorGoal.company_id == company_id,
                        IndicatorGoal.status == "active",
                    )
                ),
            ),
            warnings=warnings,
            label="indicators_with_goals",
        )
        indicators_with_data_total = BusinessReviewReadModelService._safe_count(
            Indicator.query.filter(
                Indicator.company_id == company_id,
                Indicator.is_active.is_(True),
                Indicator.id.in_(
                    db.session.query(IndicatorData.indicator_id).filter(IndicatorData.company_id == company_id)
                ),
            ),
            warnings=warnings,
            label="indicators_with_data",
        )
        data_records_total = BusinessReviewReadModelService._safe_count(
            IndicatorData.query.filter(IndicatorData.company_id == company_id),
            warnings=warnings,
            label="indicator_data",
        )
        management_meetings_total = BusinessReviewReadModelService._safe_count(
            Meeting.query.filter(
                Meeting.company_id == company_id,
                Meeting.status.notin_(["cancelled", "canceled"]),
                or_(
                    Meeting.title.ilike("%gest%o%"),
                    Meeting.title.ilike("%estrat%"),
                    Meeting.title.ilike("%indicador%"),
                    Meeting.title.ilike("%resultado%"),
                ),
            ),
            warnings=warnings,
            label="management_meetings",
        )
        active_incentive_sets_total = BusinessReviewReadModelService._safe_count(
            IncentiveRuleSet.query.filter(
                IncentiveRuleSet.company_id == company_id,
                IncentiveRuleSet.is_active.is_(True),
                IncentiveRuleSet.deleted_at.is_(None),
            ),
            warnings=warnings,
            label="active_incentive_rule_sets",
        )
        incentive_rules_total = BusinessReviewReadModelService._safe_count(
            IncentiveRule.query.filter(
                IncentiveRule.company_id == company_id,
                IncentiveRule.deleted_at.is_(None),
            ),
            warnings=warnings,
            label="incentive_rules",
        )
        governability_links_total = BusinessReviewReadModelService._safe_count(
            IncentiveGovernabilityMatrix.query.filter(IncentiveGovernabilityMatrix.company_id == company_id),
            warnings=warnings,
            label="incentive_governability_matrix",
        )
        entity_links_total = BusinessReviewReadModelService._safe_count(
            IndicatorEntityLink.query.filter(
                IndicatorEntityLink.company_id == company_id,
                IndicatorEntityLink.is_active.is_(True),
            ),
            warnings=warnings,
            label="indicator_entity_links",
        )
        line_of_sight_total = BusinessReviewReadModelService._safe_count(
            IndicatorLineOfSight.query.filter(IndicatorLineOfSight.company_id == company_id),
            warnings=warnings,
            label="indicator_line_of_sight",
        )
        strategic_projects_total = BusinessReviewReadModelService._safe_count(
            Project.query.filter(
                Project.company_id == company_id,
                Project.is_deleted.is_(False),
                or_(Project.plan_id.isnot(None), Project.okr_links.isnot(None)),
            ),
            warnings=warnings,
            label="strategic_management_projects",
        )

        indicators_ok = (
            active_indicators_total > 0
            and indicators_with_responsible_total > 0
            and indicators_with_goals_total > 0
        )
        cycles_ok = management_meetings_total > 0 or data_records_total > 0
        incentives_ok = active_incentive_sets_total > 0 and incentive_rules_total > 0
        web_ok = entity_links_total > 0 or line_of_sight_total > 0 or strategic_projects_total > 0
        checks = {
            "indicators": indicators_ok,
            "cycles": cycles_ok,
            "incentives": incentives_ok,
            "web": web_ok,
        }
        score = BusinessReviewReadModelService._pct(sum(1 for item in checks.values() if item), len(checks))
        evidence = [
            {
                "type": "indicators",
                "label": "Indicadores",
                "finding": (
                    f"{active_indicators_total} ativo(s), {indicators_with_responsible_total} com responsável, "
                    f"{indicators_with_goals_total} com meta e {indicators_with_data_total} com medição."
                ),
            },
            {
                "type": "cycles",
                "label": "Ciclos de gestão",
                "finding": f"{management_meetings_total} reunião(ões) gerenciais e {data_records_total} medição(ões).",
            },
            {
                "type": "incentives",
                "label": "Gestão de Incentivos",
                "finding": (
                    f"{active_incentive_sets_total} plano(s) ativo(s), {incentive_rules_total} regra(s) "
                    f"e {governability_links_total} vínculo(s) de governabilidade."
                ),
            },
            {
                "type": "web",
                "label": "Teia de Conexões",
                "finding": (
                    f"{entity_links_total} vínculo(s) indicador->objeto, {line_of_sight_total} linha(s) de visada "
                    f"e {strategic_projects_total} projeto(s) estratégico(s)."
                ),
            },
        ]
        gaps = BusinessReviewReadModelService._strategic_management_front_gaps(
            checks=checks,
            active_indicators_total=active_indicators_total,
            indicators_with_responsible_total=indicators_with_responsible_total,
            indicators_with_goals_total=indicators_with_goals_total,
            indicators_with_data_total=indicators_with_data_total,
            management_meetings_total=management_meetings_total,
            active_incentive_sets_total=active_incentive_sets_total,
            incentive_rules_total=incentive_rules_total,
            entity_links_total=entity_links_total,
            line_of_sight_total=line_of_sight_total,
        )
        return {
            "front": front["key"],
            "action": "analyze_front",
            "company_id": company_id,
            "summary": (
                "Gerenciamento Estratégico analisado por indicadores, ciclos de gestão, "
                "incentivos e teia de conexões entre estratégia, processos, projetos, pessoas e indicadores."
            ),
            "maturity": {
                "status": BusinessReviewReadModelService._maturity_status(score),
                "score": score,
                "basis": "Indicadores, ciclos, incentivos e teia de conexões no APP32.",
            },
            "internal_evidence": evidence,
            "gaps": gaps,
            "recommendations": BusinessReviewReadModelService._strategic_management_front_recommendations(
                checks=checks,
                active_indicators_total=active_indicators_total,
                indicators_with_responsible_total=indicators_with_responsible_total,
                indicators_with_goals_total=indicators_with_goals_total,
                indicators_with_data_total=indicators_with_data_total,
                management_meetings_total=management_meetings_total,
                active_incentive_sets_total=active_incentive_sets_total,
                incentive_rules_total=incentive_rules_total,
                entity_links_total=entity_links_total,
                line_of_sight_total=line_of_sight_total,
            ),
            "external_benchmarks": [],
            "engineering_gaps": [
                {
                    "type": "read_model_gap",
                    "severity": "medium",
                    "description": (
                        "Unificar painel estratégico, mapa de vínculos de indicadores, teia de incentivos "
                        "e ciclos de reunião em contrato canônico do Cockpit."
                    ),
                },
                {
                    "type": "method_gap",
                    "severity": "medium",
                    "description": (
                        "Ainda falta capturar decisão, ação e aprendizado por ciclo gerencial para provar "
                        "aprendizado estratégico recorrente."
                    ),
                },
            ],
            "warnings": warnings,
            "human_gate_required": True,
            "suggested_next_action": "open_maturation_plan",
            "state": "draft",
        }

    @staticmethod
    def _strategic_management_front_gaps(
        *,
        checks: dict[str, bool],
        active_indicators_total: int,
        indicators_with_responsible_total: int,
        indicators_with_goals_total: int,
        indicators_with_data_total: int,
        management_meetings_total: int,
        active_incentive_sets_total: int,
        incentive_rules_total: int,
        entity_links_total: int,
        line_of_sight_total: int,
    ) -> list[dict[str, str]]:
        gaps: list[dict[str, str]] = []
        if not active_indicators_total:
            gaps.append({"type": "indicators", "severity": "high", "description": "Não há indicadores ativos."})
        else:
            if indicators_with_responsible_total < active_indicators_total:
                gaps.append(
                    {
                        "type": "indicators",
                        "severity": "medium",
                        "description": "Há indicadores ativos sem Responsável do Indicador.",
                    }
                )
            if indicators_with_goals_total < active_indicators_total:
                gaps.append(
                    {
                        "type": "indicators",
                        "severity": "medium",
                        "description": "Há indicadores ativos sem meta/faixa de controle ativa.",
                    }
                )
            if not indicators_with_data_total:
                gaps.append(
                    {
                        "type": "cycles",
                        "severity": "medium",
                        "description": "Indicadores ainda não possuem medições suficientes para sustentar ciclos de gestão.",
                    }
                )
        if not management_meetings_total:
            gaps.append(
                {
                    "type": "cycles",
                    "severity": "medium",
                    "description": "Não há evidência de reunião/ciclo gerencial estratégico registrado.",
                }
            )
        if not checks.get("incentives"):
            gaps.append(
                {
                    "type": "incentives",
                    "severity": "medium",
                    "description": (
                        "Gestão de Incentivos ainda não está estruturada com plano ativo e regras conectadas a indicadores."
                    ),
                }
            )
        if active_incentive_sets_total and not incentive_rules_total:
            gaps.append(
                {
                    "type": "incentives",
                    "severity": "high",
                    "description": "Há plano de incentivo ativo sem regras de cálculo associadas.",
                }
            )
        if not entity_links_total and not line_of_sight_total:
            gaps.append(
                {
                    "type": "web",
                    "severity": "medium",
                    "description": "Teia de Conexões ainda não está explícita entre indicadores, estratégia, processos e projetos.",
                }
            )
        if not gaps:
            gaps.append(
                {
                    "type": "methodological",
                    "severity": "low",
                    "description": "Gerenciamento Estratégico sem gaps críticos no diagnóstico operacional inicial.",
                }
            )
        return gaps

    @staticmethod
    def _strategic_management_front_recommendations(
        *,
        checks: dict[str, bool],
        active_indicators_total: int,
        indicators_with_responsible_total: int,
        indicators_with_goals_total: int,
        indicators_with_data_total: int,
        management_meetings_total: int,
        active_incentive_sets_total: int,
        incentive_rules_total: int,
        entity_links_total: int,
        line_of_sight_total: int,
    ) -> list[dict[str, str]]:
        recommendations: list[str] = []
        if not active_indicators_total:
            recommendations.append("Cadastrar indicadores estratégicos mínimos antes de avaliar o gerenciamento.")
        else:
            if indicators_with_responsible_total < active_indicators_total:
                recommendations.append("Definir Responsável do Indicador para todos os indicadores ativos.")
            if indicators_with_goals_total < active_indicators_total:
                recommendations.append("Cadastrar metas/faixas de controle para indicadores ativos.")
            if not indicators_with_data_total:
                recommendations.append("Registrar medições para iniciar ciclos de decisão baseados em fatos.")
        if not management_meetings_total:
            recommendations.append("Instituir reunião gerencial periódica para decisão, ação e aprendizado.")
        if not active_incentive_sets_total:
            recommendations.append("Avaliar se a Gestão de Incentivos deve ser criada para alinhar comportamento à estratégia.")
        elif not incentive_rules_total:
            recommendations.append("Conectar regras de incentivo aos indicadores que realmente direcionam resultado.")
        if not entity_links_total and not line_of_sight_total:
            recommendations.append("Construir a Teia de Conexões entre estratégia, processos, projetos, pessoas e indicadores.")
        recommendations.append("Validar com o consultor se os ciclos geram decisões, ações e aprendizados rastreáveis.")
        return [
            {
                "priority": f"P{min(index + 1, 3)}",
                "description": description,
                "target_object": "strategic_management",
            }
            for index, description in enumerate(recommendations)
        ]

    @staticmethod
    def _processes_front_analysis(company_id: int, front: dict[str, Any]) -> dict[str, Any]:
        """Análise assistida da frente Processos ancorada em dados reais do APP32.

        Mantém fallback resiliente porque algumas tabelas podem ainda estar em
        rollout em ambientes diferentes.
        """
        warnings: list[str] = []
        journey: dict[str, Any] = {}
        try:
            from services.structuring_journey_service import StructuringJourneyService

            journey = StructuringJourneyService.get_journey(
                company_id=company_id,
                audience="consultant",
                scope="company",
            )
        except SQLAlchemyError as exc:
            db.session.rollback()
            warnings.append(f"structuring_journey: {exc.__class__.__name__}")
        except Exception as exc:  # pragma: no cover - proteção contra rollout parcial de tabelas legadas.
            warnings.append(f"structuring_journey: {exc.__class__.__name__}")

        active_process_filter = or_(Process.is_active.is_(True), Process.is_active.is_(None))
        areas_total = BusinessReviewReadModelService._safe_count(
            ProcessArea.query.filter(ProcessArea.company_id == company_id),
            warnings=warnings,
            label="process_areas",
        )
        macroprocesses_total = BusinessReviewReadModelService._safe_count(
            MacroProcess.query.filter(MacroProcess.company_id == company_id),
            warnings=warnings,
            label="macro_processes",
        )
        processes_total = BusinessReviewReadModelService._safe_count(
            Process.query.filter(Process.company_id == company_id, active_process_filter),
            warnings=warnings,
            label="processes",
        )
        processes_with_owner = BusinessReviewReadModelService._safe_count(
            Process.query.filter(
                Process.company_id == company_id,
                active_process_filter,
                or_(
                    Process.owner_employee_id.isnot(None),
                    Process.responsible_id.isnot(None),
                    and_(Process.responsible.isnot(None), Process.responsible != ""),
                ),
            ),
            warnings=warnings,
            label="processes_with_owner",
        )
        processes_without_owner = max(processes_total - processes_with_owner, 0)
        processes_with_modeling = BusinessReviewReadModelService._safe_count(
            Process.query.filter(
                Process.company_id == company_id,
                active_process_filter,
                or_(
                    and_(Process.flow_document.isnot(None), Process.flow_document != ""),
                    and_(Process.flow_mermaid.isnot(None), Process.flow_mermaid != ""),
                    Process.id.in_(
                        db.session.query(ProcessBpmnDiagram.process_id).filter(
                            ProcessBpmnDiagram.company_id == company_id,
                            ProcessBpmnDiagram.status != "archived",
                        )
                    ),
                ),
            ),
            warnings=warnings,
            label="processes_with_modeling",
        )
        routines_total = BusinessReviewReadModelService._safe_count(
            ProcessRoutine.query.filter(ProcessRoutine.company_id == company_id, ProcessRoutine.is_active.is_(True)),
            warnings=warnings,
            label="process_routines",
        )
        steps_total = BusinessReviewReadModelService._safe_count(
            ProcessStep.query.join(ProcessRoutine, ProcessRoutine.id == ProcessStep.routine_id).filter(
                ProcessRoutine.company_id == company_id,
                ProcessRoutine.is_active.is_(True),
            ),
            warnings=warnings,
            label="process_steps",
        )
        execution_contracts_total = BusinessReviewReadModelService._safe_count(
            ProcessActivityExecutionContract.query.filter(
                ProcessActivityExecutionContract.company_id == company_id,
                ProcessActivityExecutionContract.is_active.is_(True),
            ),
            warnings=warnings,
            label="process_activity_execution_contracts",
        )
        audit_checklists_total = BusinessReviewReadModelService._safe_count(
            AuditChecklist.query.filter(
                AuditChecklist.company_id == company_id,
                AuditChecklist.checklist_type == "process",
                AuditChecklist.active.is_(True),
            ),
            warnings=warnings,
            label="audit_checklists",
        )
        audit_schedules_total = BusinessReviewReadModelService._safe_count(
            AuditSchedule.query.filter(
                AuditSchedule.company_id == company_id,
                AuditSchedule.process_id.isnot(None),
                AuditSchedule.status.in_(["active", "paused"]),
            ),
            warnings=warnings,
            label="audit_schedules",
        )

        summary = journey.get("summary") if isinstance(journey, dict) else {}
        journey_score = summary.get("overall_maturity_pct") if isinstance(summary, dict) else None
        score = BusinessReviewReadModelService._maturity_score(journey_score or front.get("maturity"))

        evidence = [
            {"type": "architecture", "label": "Áreas cadastradas", "finding": f"{areas_total} área(s)."},
            {
                "type": "architecture",
                "label": "Macroprocessos cadastrados",
                "finding": f"{macroprocesses_total} macroprocesso(s).",
            },
            {"type": "architecture", "label": "Processos ativos", "finding": f"{processes_total} processo(s)."},
            {
                "type": "ownership",
                "label": "Processos com dono/responsável",
                "finding": f"{processes_with_owner} de {processes_total} processo(s).",
            },
            {
                "type": "modeling",
                "label": "Processos com fluxo/modelagem",
                "finding": f"{processes_with_modeling} de {processes_total} processo(s).",
            },
            {
                "type": "routine",
                "label": "Rotinas e POPs",
                "finding": f"{routines_total} rotina(s) e {steps_total} passo(s) cadastrados.",
            },
            {
                "type": "automation_contract",
                "label": "SPEC/contratos de execução",
                "finding": f"{execution_contracts_total} contrato(s) de execução de atividade.",
            },
            {
                "type": "audit",
                "label": "Auditoria interna",
                "finding": f"{audit_checklists_total} checklist(s) e {audit_schedules_total} agenda(s) de processo.",
            },
        ]

        gaps = BusinessReviewReadModelService._processes_front_gaps(
            areas_total=areas_total,
            macroprocesses_total=macroprocesses_total,
            processes_total=processes_total,
            processes_without_owner=processes_without_owner,
            processes_with_modeling=processes_with_modeling,
            routines_total=routines_total,
            audit_checklists_total=audit_checklists_total,
            audit_schedules_total=audit_schedules_total,
        )
        return {
            "front": front["key"],
            "action": "analyze_front",
            "company_id": company_id,
            "summary": (
                "Processos analisados como frente estrutural do Cockpit do Consultor, usando arquitetura de processos, "
                "modelagem, rotinas, contratos de execução, auditoria interna e evidências auxiliares N1."
            ),
            "maturity": {
                "status": BusinessReviewReadModelService._maturity_status(score),
                "score": score,
                "basis": "Cockpit do Consultor + evidências operacionais tenant-safe do APP32 + read models auxiliares N1.",
            },
            "internal_evidence": evidence,
            "gaps": gaps,
            "recommendations": BusinessReviewReadModelService._processes_front_recommendations(
                processes_total=processes_total,
                processes_without_owner=processes_without_owner,
                processes_with_modeling=processes_with_modeling,
                routines_total=routines_total,
                audit_checklists_total=audit_checklists_total,
                audit_schedules_total=audit_schedules_total,
            ),
            "external_benchmarks": [],
            "engineering_gaps": [
                {
                    "type": "read_model_gap",
                    "severity": "medium",
                    "description": (
                        "Ainda falta vínculo canônico único entre processo, projeto de implantação, "
                        "treinamento e evidência de estabilização por 3 ciclos dentro das faixas de controle."
                    ),
                },
                {
                    "type": "agentic_gap",
                    "severity": "medium",
                    "description": (
                        "A pesquisa externa profunda e benchmarks ainda devem entrar por ferramenta agentic "
                        "com registro de fontes e gate humano do consultor."
                    ),
                },
            ],
            "warnings": warnings,
            "human_gate_required": True,
            "suggested_next_action": "open_maturation_plan",
            "state": "draft",
        }

    @staticmethod
    def _processes_front_gaps(
        *,
        areas_total: int,
        macroprocesses_total: int,
        processes_total: int,
        processes_without_owner: int,
        processes_with_modeling: int,
        routines_total: int,
        audit_checklists_total: int,
        audit_schedules_total: int,
    ) -> list[dict[str, str]]:
        gaps: list[dict[str, str]] = []
        if not areas_total or not macroprocesses_total or not processes_total:
            gaps.append(
                {
                    "type": "architecture",
                    "severity": "high",
                    "description": "Arquitetura de processos ainda incompleta: áreas, macroprocessos e processos precisam existir.",
                }
            )
        if processes_without_owner:
            gaps.append(
                {
                    "type": "ownership",
                    "severity": "high",
                    "description": f"{processes_without_owner} processo(s) ativo(s) sem dono/responsável definido.",
                }
            )
        if processes_total and processes_with_modeling < processes_total:
            gaps.append(
                {
                    "type": "modeling",
                    "severity": "medium",
                    "description": "Há processos ativos sem fluxo, BPMN ou documentação de modelagem associada.",
                }
            )
        if processes_total and not routines_total:
            gaps.append(
                {
                    "type": "routine",
                    "severity": "medium",
                    "description": "Nenhuma rotina/POP ativa encontrada para sustentar a execução padronizada.",
                }
            )
        if processes_total and (not audit_checklists_total or not audit_schedules_total):
            gaps.append(
                {
                    "type": "audit",
                    "severity": "medium",
                    "description": "Processos ainda não estão plenamente conectados ao ciclo de auditoria interna.",
                }
            )
        if not gaps:
            gaps.append(
                {
                    "type": "methodological",
                    "severity": "low",
                    "description": "Frente Processos sem gaps críticos no diagnóstico operacional inicial.",
                }
            )
        return gaps

    @staticmethod
    def _processes_front_recommendations(
        *,
        processes_total: int,
        processes_without_owner: int,
        processes_with_modeling: int,
        routines_total: int,
        audit_checklists_total: int,
        audit_schedules_total: int,
    ) -> list[dict[str, str]]:
        recommendations: list[str] = []
        if not processes_total:
            recommendations.append("Iniciar pela arquitetura: cadastrar áreas, macroprocessos, processos e donos.")
        if processes_without_owner:
            recommendations.append("Definir dono/responsável para todos os processos ativos antes de avançar maturidade.")
        if processes_total and processes_with_modeling < processes_total:
            recommendations.append("Priorizar modelagem dos processos críticos: fluxo, POP, recursos, SPEC para IA e indicadores.")
        if processes_total and not routines_total:
            recommendations.append("Converter processos prioritários em rotinas/POPs operacionais treináveis.")
        if processes_total and (not audit_checklists_total or not audit_schedules_total):
            recommendations.append("Criar checklist e periodicidade para entrada dos processos no ciclo de auditoria.")
        recommendations.append("Validar implantação e estabilização com o consultor antes de declarar maturidade final.")
        return [
            {"priority": f"P{min(index + 1, 3)}", "description": description, "target_object": "processes"}
            for index, description in enumerate(recommendations)
        ]

    @staticmethod
    def _structuring_maturity_track_payload(company_id: int, warnings: list[str]) -> dict[str, Any]:
        """Leitura macro das fases 00-03 conduzidas pelo Cockpit do Consultor.

        A Jornada de Estruturação permanece apenas como read model auxiliar. A
        decisão de avanço continua exigindo evidência e gate humano consultivo.
        """
        journey: dict[str, Any] = {}
        try:
            from services.structuring_journey_service import StructuringJourneyService

            journey = StructuringJourneyService.get_journey(
                company_id=company_id,
                audience="consultant",
                scope="company",
            )
        except SQLAlchemyError as exc:
            db.session.rollback()
            warnings.append(f"structuring_maturity_track: {exc.__class__.__name__}")
        except Exception as exc:  # pragma: no cover - tolera rollout parcial da Jornada.
            warnings.append(f"structuring_maturity_track: {exc.__class__.__name__}")

        summary = journey.get("summary") if isinstance(journey, dict) else {}
        blocks = journey.get("blocks") if isinstance(journey, dict) else []
        ready_blocks = int((summary or {}).get("blocks_ready") or 0)
        blocks_total = int((summary or {}).get("blocks_total") or len(blocks or []) or 0)
        maturity_pct = int((summary or {}).get("overall_maturity_pct") or 0)
        next_missing = (summary or {}).get("next_missing") or []

        if ready_blocks <= 0:
            phase_key = "phase_00"
            phase_number = "00"
            phase_title = "Base Organizacional / empresa na mão"
            gate = "identidade mínima, organograma, responsabilidades, controle mínimo e visão inicial confiável"
            next_advance = "Validar identidade organizacional mínima, organograma, responsáveis e arquitetura inicial."
        elif ready_blocks < max(blocks_total, 1):
            phase_key = "phase_01"
            phase_number = "01"
            phase_title = "Processos finalísticos"
            gate = "cadeia de valor principal estabilizada"
            next_advance = "Concluir evidências essenciais da frente e priorizar processos críticos no Cockpit."
        elif maturity_pct < 80:
            phase_key = "phase_02"
            phase_number = "02"
            phase_title = "Todos os processos"
            gate = "operação inteira sob lógica de processo, indicador e rotina"
            next_advance = "Expandir modelagem, implantação, estabilização e auditoria para toda a operação."
        else:
            phase_key = "phase_03"
            phase_number = "03"
            phase_title = "Planejamento e gestão estratégicos"
            gate = "estratégia em ciclo vivo de decisão, ação e aprendizado"
            next_advance = "Conectar planejamento, indicadores, incentivos, projetos e teia de conexões."

        evidence_missing = [
            item.get("label") or item.get("key") or str(item)
            for item in next_missing[:5]
            if item
        ]
        if not evidence_missing:
            evidence_missing = [
                "Validar missão, visão, valores, posicionamento e organograma.",
                "Validar responsáveis principais e evidências do gate atual com o consultor.",
                "Confirmar funcionamento real antes de avançar de fase.",
            ]

        phases = [
            {"number": "00", "label": "Fase 00", "title": "Base Organizacional / empresa na mão"},
            {"number": "01", "label": "Fase 01", "title": "Processos finalísticos"},
            {"number": "02", "label": "Fase 02", "title": "Todos os processos"},
            {"number": "03", "label": "Fase 03", "title": "Planejamento e gestão estratégicos"},
        ]
        for phase in phases:
            phase["current"] = phase["number"] == phase_number
            phase["status"] = "current" if phase["current"] else "pending"
            if int(phase["number"]) < int(phase_number):
                phase["status"] = "done"

        return {
            "key": "structuring_maturity_track",
            "title": "Fases da Estruturação Empresarial",
            "current_phase": {
                "key": phase_key,
                "number": phase_number,
                "title": phase_title,
                "label": f"Fase {phase_number} — {phase_title}",
            },
            "gate": {
                "status": "Em maturação",
                "description": gate,
                "policy": "consultive_human_gate",
            },
            "maturity_pct": maturity_pct,
            "journey_summary": {
                "blocks_ready": ready_blocks,
                "blocks_total": blocks_total,
                "blocks_unlocked": int((summary or {}).get("blocks_unlocked") or 0),
                "pending_items": int((summary or {}).get("pending_items") or 0),
            },
            "next_advance": next_advance,
            "missing_evidence": evidence_missing,
            "risks": [
                "Não avançar fase por cadastro preenchido sem funcionamento comprovado.",
                "Validar o gate com evidências reais antes de comunicar maturidade ao cliente.",
            ],
            "detail_url": "/structuring-journey/consultant",
            "phases": phases,
        }

    @staticmethod
    def _structural_fronts_payload() -> list[dict[str, Any]]:
        return [
            {
                "key": front["key"],
                "title": front["title"],
                "status": front["status"],
                "maturity": front["maturity"],
                "tags": [dict(tag) for tag in front["tags"]],
            }
            for front in BusinessReviewReadModelService.STRUCTURAL_FRONTS
        ]

    @staticmethod
    def _front_by_key(front_key: str) -> dict[str, Any] | None:
        normalized = str(front_key or "").strip()
        for front in BusinessReviewReadModelService.STRUCTURAL_FRONTS:
            if front["key"] == normalized:
                return {
                    "key": front["key"],
                    "title": front["title"],
                    "status": front["status"],
                    "maturity": front["maturity"],
                    "tags": [dict(tag) for tag in front["tags"]],
                }
        return None

    @staticmethod
    def _maturity_score(value: Any) -> int:
        text = str(value or "").replace("%", "").strip()
        try:
            return max(0, min(int(float(text)), 100))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _maturity_status(score: int) -> str:
        if score >= 80:
            return "ok"
        if score >= 50:
            return "partial"
        return "draft"

    @staticmethod
    def _front_gaps(front_key: str, tags: list[dict[str, Any]]) -> list[dict[str, str]]:
        gaps: list[dict[str, str]] = []
        for tag in tags:
            status = str(tag.get("status") or "").strip()
            if status in {"pending", "review", "partial"}:
                severity = "high" if status == "pending" else "medium"
                gaps.append(
                    {
                        "type": "methodological",
                        "severity": severity,
                        "description": f"Item exige atenção: {tag.get('label')}.",
                    }
                )
        if not gaps:
            gaps.append(
                {
                    "type": "methodological",
                    "severity": "low",
                    "description": f"Frente {front_key} sem gaps críticos no diagnóstico inicial.",
                }
            )
        return gaps

    @staticmethod
    def _front_recommendations(front_key: str) -> list[dict[str, str]]:
        by_front = {
            "identity": [
                "Validar coerência entre missão, visão, valores, posicionamento e organograma com o cliente.",
                "Registrar decisão de posicionamento antes de avançar desdobramentos estratégicos mais profundos.",
            ],
            "processes": [
                "Priorizar processos com implantação em andamento e associar projeto/programa de treinamento.",
                "Evoluir estabilização com evidência de 3 ciclos dentro das faixas de controle.",
            ],
            "growth_plan": [
                "Conectar objetivos estratégicos a processos, indicadores e projetos ativos.",
                "Revisar se o planejamento está vinculado ao Gerenciamento Estratégico.",
            ],
            "strategic_management": [
                "Revisar indicadores sem ciclo de gestão ou sem decisão registrada.",
                "Avaliar incentivos e teia de conexões antes de concluir maturidade da gestão estratégica.",
            ],
        }
        return [
            {"priority": f"P{min(index + 1, 3)}", "description": description, "target_object": "maturation"}
            for index, description in enumerate(by_front.get(front_key, []))
        ]

    @staticmethod
    def _front_engineering_gaps(front_key: str) -> list[dict[str, str]]:
        by_front = {
            "identity": "Conectar o card a CompanyIdentityService/StrategyAlignmentN1Service em read model único.",
            "processes": "Criar read model específico para Arquitetura, Modelagem, Implantação, Estabilização e Auditoria.",
            "growth_plan": "Normalizar contrato entre planejamento estratégico, N1, indicadores, projetos e processos.",
            "strategic_management": "Integrar indicadores, ciclos, incentivos e teia de conexões em leitura única do Cockpit.",
        }
        return [
            {
                "type": "read_model_gap",
                "severity": "medium",
                "description": by_front.get(front_key, "Frente ainda exige contrato técnico específico."),
            }
        ]

    @staticmethod
    def _front_summary(front: dict[str, Any], gaps: list[dict[str, str]]) -> str:
        return (
            f"{front['title']} está com maturidade {front.get('maturity') or '--'} "
            f"e {len(gaps)} ponto(s) de atenção no diagnóstico inicial."
        )


    @staticmethod
    def _urgent_need_payload(item: UrgentNeedOverlay) -> dict[str, Any]:
        payload = item.to_dict()
        project = getattr(item, "project", None)
        if project is not None:
            payload["project"] = {
                "id": project.id,
                "code": getattr(project, "code", None) or f"#{project.id}",
                "name": getattr(project, "name", None),
                "status": getattr(project, "status", None),
                "progress": getattr(project, "progress", None),
                "owner": getattr(project, "owner", None),
                "program": getattr(getattr(project, "portfolio", None), "name", None),
                "created_at": project.created_at.isoformat() if getattr(project, "created_at", None) else None,
                "updated_at": project.updated_at.isoformat() if getattr(project, "updated_at", None) else None,
                "start_date": project.start_date.isoformat() if getattr(project, "start_date", None) else None,
                "end_date": project.end_date.isoformat() if getattr(project, "end_date", None) else None,
                "url": f"/projects/{project.id}/manage",
            }
        elif item.project_id:
            payload["project"] = {"id": item.project_id, "code": f"#{item.project_id}", "url": f"/projects/{item.project_id}/manage"}
        else:
            payload["project"] = None
        payload["method_flags"] = {
            "urgent_need": True,
            "business_structuring": bool(item.process_id or item.routine_id or item.indicator_id),
        }
        return payload

    @staticmethod
    def _business_review_payload(item: BusinessReviewRecord) -> dict[str, Any]:
        payload = item.to_dict()
        simple_fields = {
            "identified_need": item.title,
            "applied_solution": item.next_action,
            "achieved_result": item.structural_learning_summary,
            "added_value": item.decision_summary,
        }
        payload["simple_fields"] = simple_fields
        payload["is_registered"] = all(str(value or "").strip() for value in simple_fields.values())
        payload["captured_value"] = item.decision_summary
        return payload

    @staticmethod
    def _count_by(rows: list[Any], attr: str) -> dict[str, int]:
        counter = Counter(str(getattr(row, attr, None) or "undefined") for row in rows)
        return dict(sorted(counter.items()))

    @staticmethod
    def _money(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _financial_summary(reviews: list[BusinessReviewRecord]) -> dict[str, float]:
        return {
            "cost_to_act": round(sum(BusinessReviewReadModelService._money(item.cost_to_act) for item in reviews), 2),
            "cost_to_not_act": round(
                sum(BusinessReviewReadModelService._money(item.cost_to_not_act) for item in reviews),
                2,
            ),
            "required_investment": round(
                sum(BusinessReviewReadModelService._money(item.required_investment) for item in reviews),
                2,
            ),
            "expected_gain": round(sum(BusinessReviewReadModelService._money(item.expected_gain) for item in reviews), 2),
            "expected_return": round(
                sum(BusinessReviewReadModelService._money(item.expected_return) for item in reviews),
                2,
            ),
        }

    @staticmethod
    def _next_focus(
        *,
        open_urgent_needs: list[UrgentNeedOverlay],
        pending_reviews: list[BusinessReviewRecord],
        pending_learnings: list[StructuralLearningLink],
    ) -> list[dict[str, Any]]:
        focus: list[dict[str, Any]] = []
        critical = [item for item in open_urgent_needs if item.urgency_level == "critical"]
        if critical:
            focus.append(
                {
                    "priority": "P0",
                    "type": "urgent_need",
                    "message": f"{len(critical)} necessidade(s) urgente(s) críticas abertas exigem decisão.",
                    "item_ids": [item.id for item in critical[:10]],
                }
            )
        if pending_reviews:
            focus.append(
                {
                    "priority": "P1",
                    "type": "business_review",
                    "message": f"{len(pending_reviews)} Business Review(s) em acompanhamento.",
                    "item_ids": [item.id for item in pending_reviews[:10]],
                }
            )
        if pending_learnings:
            focus.append(
                {
                    "priority": "P1",
                    "type": "structural_learning",
                    "message": f"{len(pending_learnings)} aprendizado(s) estrutural(is) aguardam ação.",
                    "item_ids": [item.id for item in pending_learnings[:10]],
                }
            )
        if not focus:
            focus.append(
                {
                    "priority": "P3",
                    "type": "routine",
                    "message": "Sem pendências consultivas críticas no read model atual.",
                    "item_ids": [],
                }
            )
        return focus


__all__ = ["BusinessReviewReadModelService"]
