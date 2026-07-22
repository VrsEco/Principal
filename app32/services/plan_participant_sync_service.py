from __future__ import annotations

import re
import unicodedata
from typing import Any

from models import Employee, Plan, PlanParticipant, PlanSectionStatus, db


class PlanParticipantSyncError(ValueError):
    pass


class PlanParticipantSyncService:
    """Sincroniza participantes ativos de um tenant em um planejamento."""

    @staticmethod
    def _normalize(value: str) -> str:
        folded = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = "".join(char for char in folded if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_value.casefold()).strip()

    @classmethod
    def execute(
        cls,
        *,
        company_id: int,
        plan_id: int,
        owner_name: str,
        confirmed_mutation: bool,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if confirmed_mutation is not True:
            raise PermissionError("Confirmação humana explícita é obrigatória para sincronizar participantes.")
        plan = Plan.query.filter(Plan.id == int(plan_id), Plan.company_id == int(company_id)).first()
        if plan is None:
            raise PlanParticipantSyncError("Planejamento não encontrado no tenant informado.")

        employees = Employee.query.filter(Employee.company_id == int(company_id)).all()
        active = [
            item
            for item in employees
            if cls._normalize(item.status or "") in {"", "active", "ativo", "enabled", "habilitado"}
        ]
        if not active:
            raise PlanParticipantSyncError("Nenhum colaborador ativo encontrado no tenant.")
        requested_owner = cls._normalize(owner_name)
        owner_matches = [
            item
            for item in active
            if cls._normalize(item.name) == requested_owner
            or cls._normalize(item.name).split(" ", 1)[0] == requested_owner
        ]
        if len(owner_matches) != 1:
            raise PlanParticipantSyncError(
                f"Owner '{owner_name}' não possui identidade oficial única na empresa {company_id}."
            )
        owner = owner_matches[0]

        created: list[int] = []
        updated: list[int] = []
        try:
            existing = PlanParticipant.query.filter(PlanParticipant.plan_id == int(plan_id)).all()
            by_employee = {row.employee_id: row for row in existing if row.employee_id is not None}
            for employee in active:
                role = "owner" if employee.id == owner.id else "viewer"
                participant = by_employee.get(employee.id)
                if participant is None:
                    participant = PlanParticipant(
                        plan_id=int(plan_id),
                        user_id=employee.user_id,
                        employee_id=employee.id,
                        role=role,
                        meta_data={"source": "mcp_tenant_active_sync"},
                    )
                    db.session.add(participant)
                    db.session.flush()
                    created.append(participant.id)
                elif participant.role != role or participant.user_id != employee.user_id:
                    participant.role = role
                    participant.user_id = employee.user_id
                    updated.append(participant.id)

            section = PlanSectionStatus.query.filter_by(plan_id=int(plan_id), section_key="participants").first()
            if section is None:
                section = PlanSectionStatus(plan_id=int(plan_id), section_key="participants", status="completed")
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
            "owner": {"employee_id": owner.id, "name": owner.name},
            "participant_count": len(active),
            "created_participant_ids": created,
            "updated_participant_ids": updated,
            "participants": [
                {"employee_id": item.id, "name": item.name, "role": "owner" if item.id == owner.id else "viewer"}
                for item in active
            ],
            "section_status": "completed",
            "human_confirmation_applied": True,
        }


__all__ = ["PlanParticipantSyncError", "PlanParticipantSyncService"]
