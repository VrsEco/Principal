from __future__ import annotations

from datetime import datetime
from typing import Any

from models import BusinessReviewRecord, UrgentNeedOverlay, db
from models.urgent_business_review import (
    URGENT_NEED_CRITICALITY_VALUES,
    URGENT_NEED_LEVEL_VALUES,
    URGENT_NEED_STATUS_VALUES,
)
from services.urgent_business_review_common import (
    UrgentBusinessReviewError,
    clean_text,
    normalize_choice,
    validate_canonical_links,
)


class UrgentNeedService:
    """Service tenant-safe para o overlay consultivo de Necessidade Urgente."""

    @staticmethod
    def get_urgent_need(company_id: int, urgent_need_id: int) -> UrgentNeedOverlay:
        row = UrgentNeedOverlay.query.filter_by(id=urgent_need_id, company_id=company_id).first()
        if row is None:
            raise UrgentBusinessReviewError(f"Necessidade Urgente não encontrada: id={urgent_need_id}.")
        return row

    @staticmethod
    def list_urgent_needs(
        *,
        company_id: int,
        status: str | None = None,
        urgency_level: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = UrgentNeedOverlay.query.filter_by(company_id=company_id)
        if status:
            query = query.filter(
                UrgentNeedOverlay.status
                == normalize_choice(status, allowed=URGENT_NEED_STATUS_VALUES, default="inbox", field="status")
            )
        if urgency_level:
            query = query.filter(
                UrgentNeedOverlay.urgency_level
                == normalize_choice(urgency_level, allowed=URGENT_NEED_LEVEL_VALUES, default="medium", field="urgency_level")
            )
        rows = query.order_by(UrgentNeedOverlay.updated_at.desc(), UrgentNeedOverlay.id.desc()).limit(limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def create_urgent_need(
        *,
        company_id: int,
        title: str,
        description: str | None = None,
        urgency_level: str = "medium",
        criticality_level: str = "operational",
        origin_channel: str | None = None,
        origin_summary: str | None = None,
        project_id: int | None = None,
        project_task_id: int | None = None,
        process_id: int | None = None,
        process_instance_id: int | None = None,
        routine_id: int | None = None,
        indicator_id: int | None = None,
        meeting_id: int | None = None,
        occurrence_id: int | None = None,
        financial_ref_id: int | None = None,
        source_type: str | None = None,
        source_ref_id: str | None = None,
        source_payload: dict[str, Any] | None = None,
        business_impact_summary: str | None = None,
        operational_impact_summary: str | None = None,
        risk_summary: str | None = None,
        responsible_employee_id: int | None = None,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> UrgentNeedOverlay:
        normalized_title = clean_text(title)
        if not normalized_title:
            raise UrgentBusinessReviewError("Título da Necessidade Urgente é obrigatório.")

        validate_canonical_links(
            company_id=company_id,
            project_id=project_id,
            project_task_id=project_task_id,
            process_id=process_id,
            process_instance_id=process_instance_id,
            routine_id=routine_id,
            indicator_id=indicator_id,
            meeting_id=meeting_id,
            occurrence_id=occurrence_id,
            financial_ref_id=financial_ref_id,
        )

        row = UrgentNeedOverlay(
            company_id=company_id,
            title=normalized_title,
            description=clean_text(description),
            status="inbox",
            urgency_level=normalize_choice(
                urgency_level,
                allowed=URGENT_NEED_LEVEL_VALUES,
                default="medium",
                field="urgency_level",
            ),
            criticality_level=normalize_choice(
                criticality_level,
                allowed=URGENT_NEED_CRITICALITY_VALUES,
                default="operational",
                field="criticality_level",
            ),
            origin_channel=clean_text(origin_channel),
            origin_summary=clean_text(origin_summary),
            project_id=project_id,
            project_task_id=project_task_id,
            process_id=process_id,
            process_instance_id=process_instance_id,
            routine_id=routine_id,
            indicator_id=indicator_id,
            meeting_id=meeting_id,
            occurrence_id=occurrence_id,
            financial_ref_id=financial_ref_id,
            source_type=clean_text(source_type),
            source_ref_id=clean_text(source_ref_id),
            source_payload_json=source_payload or {},
            business_impact_summary=clean_text(business_impact_summary),
            operational_impact_summary=clean_text(operational_impact_summary),
            risk_summary=clean_text(risk_summary),
            decision_status="pending",
            responsible_employee_id=responsible_employee_id,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        db.session.add(row)
        db.session.flush()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def update_decision(
        *,
        company_id: int,
        urgent_need_id: int,
        decision_status: str,
        decision_summary: str | None = None,
        updated_by_user_id: int | None = None,
        commit: bool = True,
    ) -> UrgentNeedOverlay:
        row = UrgentNeedService.get_urgent_need(company_id, urgent_need_id)
        row.decision_status = clean_text(decision_status) or "pending"
        row.decision_summary = clean_text(decision_summary)
        row.updated_by_user_id = updated_by_user_id
        row.updated_at = datetime.utcnow()
        db.session.flush()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def change_status(
        *,
        company_id: int,
        urgent_need_id: int,
        status: str,
        updated_by_user_id: int | None = None,
        commit: bool = True,
    ) -> UrgentNeedOverlay:
        row = UrgentNeedService.get_urgent_need(company_id, urgent_need_id)
        normalized = normalize_choice(status, allowed=URGENT_NEED_STATUS_VALUES, default="inbox", field="status")
        if normalized == "closed":
            return UrgentNeedService.close_urgent_need(
                company_id=company_id,
                urgent_need_id=urgent_need_id,
                closed_by_user_id=updated_by_user_id,
                commit=commit,
            )
        row.status = normalized
        row.updated_by_user_id = updated_by_user_id
        row.updated_at = datetime.utcnow()
        db.session.flush()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def close_urgent_need(
        *,
        company_id: int,
        urgent_need_id: int,
        closed_by_user_id: int | None = None,
        commit: bool = True,
    ) -> UrgentNeedOverlay:
        row = UrgentNeedService.get_urgent_need(company_id, urgent_need_id)
        review_exists = BusinessReviewRecord.query.filter_by(
            company_id=company_id,
            urgent_need_id=urgent_need_id,
        ).first()
        if review_exists is None:
            raise UrgentBusinessReviewError("Necessidade Urgente só pode ser encerrada após alimentar Business Review.")
        row.status = "closed"
        row.closed_by_user_id = closed_by_user_id
        row.updated_by_user_id = closed_by_user_id
        row.closed_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        db.session.flush()
        if commit:
            db.session.commit()
        return row


__all__ = ["UrgentNeedService"]
