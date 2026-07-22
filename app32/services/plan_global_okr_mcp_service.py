from __future__ import annotations

import re
import unicodedata
from typing import Any

from models import OKRArea, OKRGlobal, Plan, PlanSectionStatus, db


class PlanGlobalOKRMCPService:
    @staticmethod
    def _normalize(value: str) -> str:
        folded = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = "".join(char for char in folded if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_value.casefold()).strip()

    @classmethod
    def create_and_link(
        cls,
        *,
        company_id: int,
        plan_id: int,
        okrs: list[dict[str, Any]],
        confirmed_mutation: bool,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if confirmed_mutation is not True:
            raise PermissionError("Confirmação humana explícita é obrigatória para cadastrar OKRs Globais.")
        plan = Plan.query.filter(
            Plan.id == int(plan_id), Plan.company_id == int(company_id), Plan.mode == "growth"
        ).first()
        if plan is None:
            raise ValueError("Planejamento growth não encontrado no tenant informado.")
        if not isinstance(okrs, list) or len(okrs) != 2:
            raise ValueError("Devem ser informados exatamente dois OKRs Globais.")

        prepared: list[tuple[dict[str, Any], OKRArea]] = []
        for item in okrs:
            objective = str(item.get("objective") or "").strip()
            area_okr_id = item.get("area_okr_id")
            if not objective or area_okr_id is None:
                raise ValueError("objective e area_okr_id são obrigatórios para cada OKR Global.")
            area = OKRArea.query.filter(
                OKRArea.id == int(area_okr_id),
                OKRArea.company_id == int(company_id),
                OKRArea.plan_id == int(plan_id),
            ).first()
            if area is None:
                raise ValueError(f"OKR de Área {area_okr_id} não pertence ao planejamento informado.")
            prepared.append((item, area))

        created: list[int] = []
        reused: list[int] = []
        links: list[dict[str, int]] = []
        try:
            existing_globals = OKRGlobal.query.filter(OKRGlobal.company_id == int(company_id)).all()
            for item, area in prepared:
                objective = str(item["objective"]).strip()
                matches = [
                    row for row in existing_globals
                    if cls._normalize(row.objective) == cls._normalize(objective)
                ]
                if len(matches) > 1:
                    raise ValueError(f"OKR Global duplicado preexistente: {objective}")
                if matches:
                    global_okr = matches[0]
                    if global_okr.plan_id != int(plan_id):
                        raise ValueError(f"OKR Global existente pertence a outro planejamento: {objective}")
                    reused.append(global_okr.id)
                else:
                    global_okr = OKRGlobal(
                        company_id=int(company_id),
                        plan_id=int(plan_id),
                        objective=objective,
                        type="estruturante",
                        owner=None,
                        observations="OKR Global confirmado para desdobramento setorial.",
                        directionals=[],
                    )
                    db.session.add(global_okr)
                    db.session.flush()
                    existing_globals.append(global_okr)
                    created.append(global_okr.id)
                linked_ids = [int(value) for value in (area.linked_okr_ids or [])]
                if global_okr.id not in linked_ids:
                    linked_ids.append(global_okr.id)
                    area.linked_okr_ids = linked_ids
                links.append({"global_okr_id": global_okr.id, "area_okr_id": area.id})

            section = PlanSectionStatus.query.filter_by(plan_id=int(plan_id), section_key="okrs_global").first()
            if section is None:
                section = PlanSectionStatus(plan_id=int(plan_id), section_key="okrs_global", status="completed")
                db.session.add(section)
            else:
                section.status = "completed"
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {
            "company_id": int(company_id),
            "plan_id": int(plan_id),
            "user_id": user_id,
            "created_global_okr_ids": created,
            "reused_global_okr_ids": reused,
            "links": links,
            "section_status": "completed",
            "human_confirmation_applied": True,
        }


__all__ = ["PlanGlobalOKRMCPService"]
