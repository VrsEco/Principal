from __future__ import annotations

from typing import Any

from models.consultive_assisted_analysis import CONSULTIVE_FRONT_KEY_VALUES
from services.business_review_read_model_service import BusinessReviewReadModelService
from services.consultive_assisted_analysis_service import ConsultiveAssistedAnalysisService
from services.consultive_protocol_service import ConsultiveProtocolService
from services.urgent_business_review_common import UrgentBusinessReviewError


class ConsultiveMaturityGuidanceService:
    """Motor determinístico de próxima ação da maturidade assistida."""

    DEFAULT_SUBPHASES = {
        "identity": "mission",
        "processes": "architecture",
        "growth_plan": "structured",
        "strategic_management": "indicators",
    }

    @classmethod
    def get_next_action(
        cls,
        *,
        company_id: int,
        front_key: str,
        subphase_key: str | None = None,
    ) -> dict[str, Any]:
        normalized_front = str(front_key or "").strip().lower()
        if normalized_front not in CONSULTIVE_FRONT_KEY_VALUES:
            raise UrgentBusinessReviewError(f"Frente consultiva inválida: {front_key}.")
        normalized_subphase = ConsultiveProtocolService._normalize_subphase(
            subphase_key or cls.DEFAULT_SUBPHASES[normalized_front]
        )
        context = BusinessReviewReadModelService.get_structural_front_analysis(
            company_id=company_id,
            front_key=normalized_front,
        )
        protocol = ConsultiveProtocolService.resolve_protocol(
            company_id=company_id,
            front_key=normalized_front,
            subphase_key=normalized_subphase,
            audience="ai_cli",
        )
        analyses = ConsultiveAssistedAnalysisService.list_analyses(
            company_id=company_id,
            front_key=normalized_front,
            limit=100,
        )
        latest = cls._latest_applicable_analysis(analyses, normalized_subphase)
        engineering_required = cls._engineering_validation_required(context)
        journey_state, action = cls._resolve_state_and_action(
            latest=latest,
            context=context,
            protocol=protocol,
            engineering_required=engineering_required,
        )
        validations = cls._validation_map(latest)
        decision = dict((latest or {}).get("latest_decision") or {}) or None
        coverage = cls._registration_coverage(context)
        methodological_maturity = cls._methodological_maturity(
            journey_state=journey_state,
            context=context,
            latest=latest,
            validations=validations,
            decision=decision,
            engineering_required=engineering_required,
        )
        return {
            "company_id": company_id,
            "front_key": normalized_front,
            "subphase_key": normalized_subphase,
            "journey_version": "mission-maturity-v1.1" if (normalized_front, normalized_subphase) == ("identity", "mission") else "structuring-journey-v2",
            "pilot_scope": (normalized_front, normalized_subphase) == ("identity", "mission"),
            "protocol": {
                "id": protocol.get("id"),
                "version": protocol.get("protocol_version"),
                "source": protocol.get("source"),
                "title": protocol.get("title"),
                "depth_level": protocol.get("depth_level"),
                "investigation_layers": list((protocol.get("protocol") or {}).get("investigation_layers") or []),
                "required_questions": list((protocol.get("protocol") or {}).get("required_questions") or []),
            },
            "journey_state": journey_state,
            "current_state": {
                "coverage": coverage,
                "methodological_maturity": methodological_maturity,
                "maturity": coverage,
                "evidence_count": len(context.get("internal_evidence") or []),
                "gap_count": len(context.get("gaps") or []),
                "engineering_gap_count": len(context.get("engineering_gaps") or []),
                "latest_analysis_id": (latest or {}).get("id"),
                "latest_analysis_status": (latest or {}).get("status"),
                "validations": validations,
                "engineering_validation_required": engineering_required,
                "consultant_decision": decision,
            },
            "next_action": action,
            "orchestration": {
                "may_execute": list(action.get("allowed_tools") or []),
                "must_not_execute": [
                    "validar por outro squad",
                    "decidir em nome do consultor",
                    "persistir dado canônico sem autorização",
                    "declarar conclusão sem releitura equivalente",
                ],
                "handoff_to": action.get("responsible"),
                "blocked": journey_state == "blocked",
                "human_gate_required": bool(action.get("human_gate_required")),
            },
        }

    @staticmethod
    def _latest_applicable_analysis(analyses: list[dict[str, Any]], subphase_key: str | None) -> dict[str, Any] | None:
        for analysis in analyses:
            snapshot = dict(analysis.get("protocol_snapshot") or {})
            analysis_subphase = snapshot.get("subphase_key")
            if analysis_subphase in (None, "", subphase_key):
                return analysis
        return None

    @staticmethod
    def _engineering_validation_required(context: dict[str, Any]) -> bool:
        return any(
            str(item.get("severity") or "").lower() in {"high", "critical"}
            for item in context.get("engineering_gaps") or []
        )

    @staticmethod
    def _validation_map(latest: dict[str, Any] | None) -> dict[str, str]:
        result = {"client": "missing", "versus": "missing", "engineering": "missing"}
        for item in (latest or {}).get("validations") or []:
            squad = str(item.get("squad") or "").lower()
            if squad in result:
                result[squad] = str(item.get("status") or "pending").lower()
        return result

    @classmethod
    def _resolve_state_and_action(
        cls,
        *,
        latest: dict[str, Any] | None,
        context: dict[str, Any],
        protocol: dict[str, Any],
        engineering_required: bool,
    ) -> tuple[str, dict[str, Any]]:
        if latest is None:
            protocol_data = dict(protocol.get("protocol") or {})
            return "collecting_evidence", cls._action(
                key="develop_mission_diagnosis",
                label="Diagnosticar e amadurecer a Missão",
                responsible="Squad Cliente / gestor / CLI do cliente",
                objective="Entender a intenção do gestor, pesquisar referências e confrontar a promessa com a capacidade real de entrega.",
                required_inputs=[
                    *list(protocol_data.get("required_questions") or []),
                    "Evidências de MVV, posicionamento, processos, pessoas e mercado.",
                    "Fontes, premissas e limitações dos benchmarks utilizados.",
                ],
                allowed_tools=[
                    "consultive_get_front_context",
                    "consultive_get_front_evidence",
                    "consultive_get_front_gaps",
                    "consultive_resolve_protocol",
                    "consultive_register_assisted_analysis",
                ],
                write_policy=cls._write_policy(
                    "consultive_register_assisted_analysis",
                    canonical_write_allowed=False,
                ),
                completion_criteria=[
                    "Perguntas obrigatórias respondidas ou marcadas como pendentes.",
                    "Fala humana separada de dado APP32, benchmark e hipótese de IA.",
                    "Diagnóstico, riscos e proposta apresentados ao gestor antes de qualquer escrita.",
                    "Confirmação humana explícita obtida para registrar a análise assistida.",
                ],
                human_gate_required=True,
            )

        validations = cls._validation_map(latest)
        for squad, status in validations.items():
            if status in {"rejected", "needs_adjustment"}:
                return "blocked", cls._action(
                    key="revise_assisted_analysis",
                    label="Revisar a análise assistida",
                    responsible=cls._squad_label(squad),
                    objective="Corrigir os pontos rejeitados ou que exigem ajuste antes de novo handoff.",
                    required_inputs=["Notas da validação", "Evidências ou fontes corrigidas", "Nova versão rastreável da análise"],
                    allowed_tools=[
                        "consultive_list_assisted_analyses",
                        "consultive_get_front_context",
                        "consultive_register_assisted_analysis",
                    ],
                    completion_criteria=["Ajustes respondidos, confirmados e registrados em nova análise rastreável."],
                    human_gate_required=True,
                    write_policy=cls._write_policy(
                        "consultive_register_assisted_analysis",
                        canonical_write_allowed=False,
                    ),
                )

        if validations["client"] != "validated":
            return "awaiting_client_validation", cls._validation_action("client", latest)
        if validations["versus"] != "validated":
            return "awaiting_versus_validation", cls._validation_action("versus", latest)
        if engineering_required and validations["engineering"] != "validated":
            return "awaiting_engineering_validation", cls._validation_action("engineering", latest)

        decision = dict(latest.get("latest_decision") or {})
        if not decision:
            return "awaiting_consultant_decision", cls._action(
                key="request_consultant_decision",
                label="Submeter ao gate do consultor",
                responsible="Consultor Versus",
                objective="Decidir aceitar, ajustar, manter ou rejeitar a recomendação validada pelos Squads.",
                required_inputs=["Análise assistida", "Validações aplicáveis", "Riscos, fontes e proposta exata"],
                allowed_tools=["consultive_list_assisted_analyses", "consultive_register_consultant_decision"],
                completion_criteria=["Decisão, justificativa e escopo autorizado registrados."],
                human_gate_required=True,
                write_policy=cls._write_policy(
                    "consultive_register_consultant_decision",
                    canonical_write_allowed=False,
                ),
            )

        if decision.get("decision") != "accept":
            return "blocked", cls._action(
                key="apply_consultant_direction",
                label="Aplicar direcionamento do consultor",
                responsible="Squad Versus",
                objective="Tratar a decisão de ajuste, espera ou rejeição sem persistir conteúdo não aprovado.",
                required_inputs=["Decisão e justificativa do consultor", "Próxima ação registrada"],
                allowed_tools=["consultive_list_assisted_analyses", "consultive_get_front_context"],
                completion_criteria=["Direcionamento tratado e novo ciclo aberto somente quando autorizado."],
                human_gate_required=True,
            )

        if str(latest.get("status") or "").lower() in {"converted", "archived"}:
            return "executed_verified", cls._action(
                key="advance_to_next_subphase",
                label="Avançar para a próxima subfase",
                responsible="Consultor Versus / Squad Cliente",
                objective="Confirmar a maturidade atualizada e iniciar a próxima subfase aplicável.",
                required_inputs=["Leitura pós-execução", "Evidência de persistência", "Maturidade recalculada"],
                allowed_tools=["consultive_get_front_context", "consultive_get_next_action"],
                completion_criteria=["Resultado verificado e próximo protocolo selecionado."],
            )

        return "approved_for_execution", cls._action(
            key="persist_approved_mission",
            label="Persistir e verificar a Missão aprovada",
            responsible="Executor autorizado / Consultor Versus",
            objective="Gravar somente o conteúdo expressamente aprovado e confirmar a persistência por releitura.",
            required_inputs=["Texto exato aprovado", "Decisão do consultor", "Executor e tenant confirmados"],
            allowed_tools=["get_strategy_identity_tool", "upsert_strategy_identity_tool", "consultive_get_front_context"],
            completion_criteria=["Missão persistida no company_id correto", "Releitura equivalente sem divergência", "Maturidade recalculada"],
            human_gate_required=True,
            write_policy=cls._write_policy(
                "upsert_strategy_identity_tool",
                canonical_write_allowed=True,
            ),
        )

    @classmethod
    def _validation_action(cls, squad: str, latest: dict[str, Any]) -> dict[str, Any]:
        labels = {
            "client": ("Validar conteúdo humano e realidade operacional", "Gestor / Squad Cliente"),
            "versus": ("Validar método e recomendação", "Squad Versus"),
            "engineering": ("Validar base técnica e rastreabilidade", "Squad de Engenharia"),
        }
        label, responsible = labels[squad]
        return cls._action(
            key=f"validate_{squad}_analysis",
            label=label,
            responsible=responsible,
            objective="Confirmar, rejeitar ou solicitar ajuste dentro do escopo exclusivo do responsável.",
            required_inputs=[f"Análise assistida #{latest.get('id')}", "Evidências, fontes, riscos e perguntas pendentes"],
            allowed_tools=[
                "consultive_list_assisted_analyses",
                "consultive_get_front_context",
                "consultive_register_squad_validation",
            ],
            completion_criteria=[f"Validação do {responsible} registrada com status e notas."],
            human_gate_required=True,
            write_policy=cls._write_policy(
                "consultive_register_squad_validation",
                canonical_write_allowed=False,
            ),
        )

    @staticmethod
    def _registration_coverage(context: dict[str, Any]) -> dict[str, Any]:
        coverage = dict(context.get("maturity") or {})
        coverage.update(
            {
                "metric_type": "registration_coverage",
                "meaning": "Presença e preenchimento dos elementos no APP32.",
                "does_not_prove_methodological_maturity": True,
            }
        )
        return coverage

    @classmethod
    def _methodological_maturity(
        cls,
        *,
        journey_state: str,
        context: dict[str, Any],
        latest: dict[str, Any] | None,
        validations: dict[str, str],
        decision: dict[str, Any] | None,
        engineering_required: bool,
    ) -> dict[str, Any]:
        gaps = list(context.get("gaps") or [])
        engineering_gaps = list(context.get("engineering_gaps") or [])
        reasons: list[str] = []
        if latest is None:
            reasons.append("assisted_analysis_missing")
        if gaps:
            reasons.append("content_gaps_open")
        if engineering_gaps:
            reasons.append("engineering_gaps_open")
        if latest is not None and validations.get("client") != "validated":
            reasons.append("client_validation_missing")
        if latest is not None and validations.get("versus") != "validated":
            reasons.append("versus_validation_missing")
        if latest is not None and engineering_required and validations.get("engineering") != "validated":
            reasons.append("engineering_validation_missing")
        if latest is not None and not decision:
            reasons.append("consultant_decision_missing")
        if journey_state != "executed_verified":
            reasons.append("execution_not_verified")

        status_by_state = {
            "collecting_evidence": "in_development",
            "awaiting_client_validation": "in_validation",
            "awaiting_versus_validation": "in_validation",
            "awaiting_engineering_validation": "in_validation",
            "awaiting_consultant_decision": "awaiting_decision",
            "approved_for_execution": "approved_pending_execution",
            "executed_verified": "mature" if not gaps and not engineering_gaps else "executed_with_open_gaps",
            "blocked": "blocked",
        }
        is_mature = journey_state == "executed_verified" and not gaps and not engineering_gaps
        return {
            "status": status_by_state.get(journey_state, "in_development"),
            "is_mature": is_mature,
            "score": None,
            "score_policy": "not_derived_from_registration_coverage",
            "open_reasons": reasons,
        }

    @staticmethod
    def _squad_label(squad: str) -> str:
        return {"client": "Gestor / Squad Cliente", "versus": "Squad Versus", "engineering": "Squad de Engenharia"}.get(squad, squad)

    @staticmethod
    def _action(
        *,
        key: str,
        label: str,
        responsible: str,
        objective: str,
        required_inputs: list[str],
        allowed_tools: list[str],
        completion_criteria: list[str],
        human_gate_required: bool = False,
        write_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "responsible": responsible,
            "objective": objective,
            "required_inputs": required_inputs,
            "allowed_tools": allowed_tools,
            "completion_criteria": completion_criteria,
            "human_gate_required": human_gate_required,
            "write_policy": write_policy or {
                "write_tools": [],
                "requires_explicit_human_confirmation": False,
                "canonical_write_allowed": False,
            },
        }

    @staticmethod
    def _write_policy(tool_name: str, *, canonical_write_allowed: bool) -> dict[str, Any]:
        return {
            "write_tools": [tool_name],
            "requires_explicit_human_confirmation": True,
            "canonical_write_allowed": canonical_write_allowed,
        }


__all__ = ["ConsultiveMaturityGuidanceService"]
