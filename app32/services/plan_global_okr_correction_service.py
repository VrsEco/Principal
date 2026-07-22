from __future__ import annotations

from typing import Any

from models import OKRArea, OKRGlobal, Plan, db


class PlanGlobalOKRCorrectionService:
    """Corrige atomicamente os dois OKRs Globais e seus desdobramentos setoriais."""

    @classmethod
    def execute(
        cls,
        *,
        company_id: int,
        plan_id: int,
        revenue_objective: str,
        profit_objective: str,
        derived_area_okr_ids: list[int],
        confirmed_mutation: bool,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if confirmed_mutation is not True:
            raise PermissionError("Confirmação humana explícita é obrigatória para corrigir os OKRs Globais.")
        plan = Plan.query.filter(
            Plan.id == int(plan_id), Plan.company_id == int(company_id), Plan.mode == "growth"
        ).first()
        if plan is None:
            raise ValueError("Planejamento growth não encontrado no tenant informado.")
        revenue_objective = str(revenue_objective or "").strip()
        profit_objective = str(profit_objective or "").strip()
        if not revenue_objective or not profit_objective or revenue_objective == profit_objective:
            raise ValueError("Os dois objetivos globais devem ser distintos e não vazios.")
        normalized_area_ids = sorted({int(value) for value in derived_area_okr_ids})
        areas = OKRArea.query.filter(
            OKRArea.company_id == int(company_id),
            OKRArea.plan_id == int(plan_id),
            OKRArea.id.in_(normalized_area_ids),
        ).all()
        if len(areas) != len(normalized_area_ids):
            raise ValueError("Um ou mais OKRs de Área não pertencem ao planejamento informado.")
        global_okrs = (
            OKRGlobal.query.filter(
                OKRGlobal.company_id == int(company_id),
                OKRGlobal.plan_id == int(plan_id),
            )
            .order_by(OKRGlobal.id)
            .all()
        )
        if len(global_okrs) != 2:
            raise ValueError("A correção exige exatamente dois OKRs Globais preexistentes no plano.")
        revenue_okr, profit_okr = global_okrs
        before = [
            {"id": item.id, "objective": item.objective, "type": item.type}
            for item in global_okrs
        ]

        try:
            revenue_okr.objective = revenue_objective
            revenue_okr.type = "estruturante"
            revenue_okr.observations = "OKR Global de crescimento confirmado pelo usuário."
            profit_okr.objective = profit_objective
            profit_okr.type = "estruturante"
            profit_okr.observations = "OKR Global de lucro líquido e destinação do resultado confirmado pelo usuário."
            for area in areas:
                area.linked_okr_ids = [revenue_okr.id]
            db.session.commit()
            from services.plan_service import PlanService

            PlanService._recalculate_progress(int(plan_id), company_id=int(company_id))
        except Exception:
            db.session.rollback()
            raise

        return {
            "company_id": int(company_id),
            "plan_id": int(plan_id),
            "user_id": user_id,
            "before": before,
            "after": [
                {"id": revenue_okr.id, "objective": revenue_okr.objective, "type": revenue_okr.type},
                {"id": profit_okr.id, "objective": profit_okr.objective, "type": profit_okr.type},
            ],
            "area_links": [
                {"area_okr_id": area.id, "global_okr_ids": list(area.linked_okr_ids or [])}
                for area in sorted(areas, key=lambda item: item.id)
            ],
            "human_confirmation_applied": True,
        }


__all__ = ["PlanGlobalOKRCorrectionService"]
