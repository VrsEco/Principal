"""Canonical, read-only Sapiens Engenharia triage guidance."""
from __future__ import annotations

from typing import Any

from services.engineering_task_router_service import EngineeringTaskRouterService
from services.engineering_token_economy_service import EngineeringTokenEconomyService


class SapiensEngineeringGuidanceService:
    """Describe the local SE-COORD contract without invoking or authorizing it."""

    @staticmethod
    def build_manifest() -> dict[str, Any]:
        return {
            "status": "local_advisory_only",
            "entry_agent": "SE-COORD",
            "interaction_mode": "orientation_only",
            "local_entrypoint": "scripts/assess_engineering_task.py",
            "input": {
                "required": ("task_id", "objective"),
                "optional": ("task_intent", "files", "domain_hints"),
                "task_intent_values": ("execution", "correction", "planning"),
            },
            "output": ("complexity", "risk", "token_economy"),
            "token_economy_strategies": (
                "minimal_active",
                "symbol_and_delta",
                "architecture_then_expand",
                "clarify_before_expand",
            ),
            "model_selection": "manual_outside_assessment",
            "requires_authenticated_mcp_for_company_evidence": True,
            "reads_operational_data": False,
            "grants_permissions": False,
            "executes_specialists": False,
        }

    @classmethod
    def build_activation_guidance(cls) -> str:
        return (
            "Informe objetivo, intenção (execution/correction/planning) e referências mínimas. "
            "O SE-COORD retorna complexidade e plano de contexto; a escolha do modelo é manual. "
            "Esta ativação não executa especialistas nem acessa dados operacionais."
        )

    @classmethod
    def assess_guided_task(cls, task: dict[str, Any]) -> dict[str, Any]:
        """Return the intentionally narrow guided result for an engineering request."""
        if not isinstance(task, dict):
            raise ValueError("Triagem guiada requer um objeto de tarefa.")
        forbidden = {"company_id", "context_scope", "runtime_profile", "surface", "user_id", "role"}
        if forbidden.intersection(task):
            raise ValueError("Triagem guiada não aceita campos de contexto ou autoridade.")
        assessment = EngineeringTaskRouterService.assess(task)
        advice = EngineeringTokenEconomyService.advise(assessment)
        return {
            "status": "assessed_not_executed",
            "entry_agent": "SE-COORD",
            "task_intent": assessment.task_intent,
            "complexity": assessment.complexity,
            "risk": assessment.risk,
            "requires_clarification": assessment.requires_clarification,
            "unknowns": assessment.unknowns,
            "token_economy": advice.model_dump(mode="json"),
            "model_selection": "manual_outside_assessment",
            "grants_permissions": False,
            "executes_specialists": False,
            "reads_operational_data": False,
        }


__all__ = ["SapiensEngineeringGuidanceService"]
