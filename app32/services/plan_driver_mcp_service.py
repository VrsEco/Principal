from __future__ import annotations

import re
import unicodedata
from typing import Any

from models import Plan, PlanDriver, PlanSectionStatus, db


class PlanDriverMCPService:
    @staticmethod
    def _normalize(value: str) -> str:
        folded = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = "".join(char for char in folded if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_value.casefold()).strip()

    @classmethod
    def create_single_driver(
        cls,
        *,
        company_id: int,
        plan_id: int,
        description: str,
        review_date: str | None,
        confirmed_mutation: bool,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if confirmed_mutation is not True:
            raise PermissionError("Confirmação humana explícita é obrigatória para cadastrar o direcionador.")
        plan = Plan.query.filter(
            Plan.id == int(plan_id), Plan.company_id == int(company_id), Plan.mode == "growth"
        ).first()
        if plan is None:
            raise ValueError("Planejamento growth não encontrado no tenant informado.")
        description = str(description or "").strip()
        if not description:
            raise ValueError("description é obrigatória.")

        existing = PlanDriver.query.filter(PlanDriver.plan_id == int(plan_id)).all()
        matches = [item for item in existing if cls._normalize(item.description) == cls._normalize(description)]
        if len(matches) > 1:
            raise ValueError("Há direcionadores duplicados no planejamento; operação abortada.")
        if existing and not matches:
            raise ValueError("O plano já possui outro direcionador; nenhum registro foi removido ou substituído.")

        try:
            if matches:
                driver = matches[0]
                created = False
            else:
                driver = PlanDriver(
                    plan_id=int(plan_id),
                    type="driver",
                    description=description,
                    priority="medium",
                    meta_data={"review_date": review_date, "source": "meeting_review"},
                )
                db.session.add(driver)
                db.session.flush()
                created = True
            section = PlanSectionStatus.query.filter_by(plan_id=int(plan_id), section_key="drivers").first()
            if section is None:
                section = PlanSectionStatus(plan_id=int(plan_id), section_key="drivers", status="completed")
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
            "created": created,
            "driver": driver.to_dict(),
            "section_status": "completed",
            "human_confirmation_applied": True,
        }


__all__ = ["PlanDriverMCPService"]
