from __future__ import annotations

from datetime import datetime
from typing import Any

from models import BusinessReviewRecord, UrgentNeedOverlay, db
from models.urgent_business_review import BUSINESS_REVIEW_STATUS_VALUES, BUSINESS_REVIEW_TYPE_VALUES
from services.urgent_business_review_common import (
    UrgentBusinessReviewError,
    clean_text,
    decimal_or_none,
    normalize_choice,
    validate_canonical_links,
)


class BusinessReviewService:
    """Service tenant-safe para Business Review da Camada Consultiva/Evolutiva."""

    @staticmethod
    def get_review(company_id: int, review_id: int) -> BusinessReviewRecord:
        row = BusinessReviewRecord.query.filter_by(id=review_id, company_id=company_id).first()
        if row is None:
            raise UrgentBusinessReviewError(f"Business Review não encontrado: id={review_id}.")
        return row

    @staticmethod
    def list_reviews(
        *,
        company_id: int,
        status: str | None = None,
        review_type: str | None = None,
        urgent_need_id: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = BusinessReviewRecord.query.filter_by(company_id=company_id)
        if status:
            query = query.filter(
                BusinessReviewRecord.status
                == normalize_choice(status, allowed=BUSINESS_REVIEW_STATUS_VALUES, default="draft", field="status")
            )
        if review_type:
            query = query.filter(
                BusinessReviewRecord.review_type
                == normalize_choice(
                    review_type,
                    allowed=BUSINESS_REVIEW_TYPE_VALUES,
                    default="urgent_need",
                    field="review_type",
                )
            )
        if urgent_need_id:
            query = query.filter(BusinessReviewRecord.urgent_need_id == urgent_need_id)
        rows = query.order_by(BusinessReviewRecord.updated_at.desc(), BusinessReviewRecord.id.desc()).limit(limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def create_review(
        *,
        company_id: int,
        title: str,
        review_type: str = "urgent_need",
        status: str = "draft",
        urgent_need_id: int | None = None,
        project_id: int | None = None,
        project_task_id: int | None = None,
        process_id: int | None = None,
        indicator_id: int | None = None,
        meeting_id: int | None = None,
        cost_to_act: Any = None,
        cost_to_not_act: Any = None,
        required_investment: Any = None,
        expected_gain: Any = None,
        expected_return: Any = None,
        risk_level: str = "medium",
        risk_acceptance_decision: bool = False,
        risk_acceptance_reason: str | None = None,
        decision_summary: str | None = None,
        structural_learning_summary: str | None = None,
        next_action: str | None = None,
        responsible_employee_id: int | None = None,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> BusinessReviewRecord:
        normalized_title = clean_text(title)
        if not normalized_title:
            raise UrgentBusinessReviewError("Título do Business Review é obrigatório.")

        urgent_need = None
        if urgent_need_id:
            urgent_need = UrgentNeedOverlay.query.filter_by(id=urgent_need_id, company_id=company_id).first()
            if urgent_need is None:
                raise UrgentBusinessReviewError(f"Necessidade Urgente não encontrada: id={urgent_need_id}.")
            project_id = project_id or urgent_need.project_id
            project_task_id = project_task_id or urgent_need.project_task_id
            process_id = process_id or urgent_need.process_id
            indicator_id = indicator_id or urgent_need.indicator_id
            meeting_id = meeting_id or urgent_need.meeting_id

        validate_canonical_links(
            company_id=company_id,
            project_id=project_id,
            project_task_id=project_task_id,
            process_id=process_id,
            indicator_id=indicator_id,
            meeting_id=meeting_id,
            require_any=urgent_need_id is None,
        )

        if risk_acceptance_decision and not clean_text(risk_acceptance_reason):
            raise UrgentBusinessReviewError("Aceite de risco exige justificativa.")

        row = BusinessReviewRecord(
            company_id=company_id,
            title=normalized_title,
            review_type=normalize_choice(
                review_type,
                allowed=BUSINESS_REVIEW_TYPE_VALUES,
                default="urgent_need",
                field="review_type",
            ),
            status=normalize_choice(status, allowed=BUSINESS_REVIEW_STATUS_VALUES, default="draft", field="status"),
            urgent_need_id=urgent_need_id,
            project_id=project_id,
            project_task_id=project_task_id,
            process_id=process_id,
            indicator_id=indicator_id,
            meeting_id=meeting_id,
            cost_to_act=decimal_or_none(cost_to_act, field="cost_to_act"),
            cost_to_not_act=decimal_or_none(cost_to_not_act, field="cost_to_not_act"),
            required_investment=decimal_or_none(required_investment, field="required_investment"),
            expected_gain=decimal_or_none(expected_gain, field="expected_gain"),
            expected_return=decimal_or_none(expected_return, field="expected_return"),
            risk_level=clean_text(risk_level) or "medium",
            risk_acceptance_decision=bool(risk_acceptance_decision),
            risk_acceptance_reason=clean_text(risk_acceptance_reason),
            decision_summary=clean_text(decision_summary),
            structural_learning_summary=clean_text(structural_learning_summary),
            next_action=clean_text(next_action),
            responsible_employee_id=responsible_employee_id,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        db.session.add(row)
        if urgent_need and urgent_need.status in {"inbox", "triage"}:
            urgent_need.status = "in_review"
            urgent_need.updated_by_user_id = created_by_user_id
            urgent_need.updated_at = datetime.utcnow()
        db.session.flush()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def update_review_decision(
        *,
        company_id: int,
        review_id: int,
        status: str,
        title: str | None = None,
        decision_summary: str | None = None,
        structural_learning_summary: str | None = None,
        next_action: str | None = None,
        risk_acceptance_decision: bool | None = None,
        risk_acceptance_reason: str | None = None,
        reviewed_by_user_id: int | None = None,
        commit: bool = True,
    ) -> BusinessReviewRecord:
        row = BusinessReviewService.get_review(company_id, review_id)
        if risk_acceptance_decision is not None:
            row.risk_acceptance_decision = bool(risk_acceptance_decision)
        if risk_acceptance_reason is not None:
            row.risk_acceptance_reason = clean_text(risk_acceptance_reason)
        if row.risk_acceptance_decision and not clean_text(row.risk_acceptance_reason):
            raise UrgentBusinessReviewError("Aceite de risco exige justificativa.")

        row.status = normalize_choice(status, allowed=BUSINESS_REVIEW_STATUS_VALUES, default="draft", field="status")
        row.title = clean_text(title) or row.title
        row.decision_summary = clean_text(decision_summary) or row.decision_summary
        row.structural_learning_summary = clean_text(structural_learning_summary) or row.structural_learning_summary
        row.next_action = clean_text(next_action) or row.next_action
        row.reviewed_by_user_id = reviewed_by_user_id or row.reviewed_by_user_id
        row.updated_by_user_id = reviewed_by_user_id or row.updated_by_user_id
        row.reviewed_at = row.reviewed_at or datetime.utcnow()
        row.updated_at = datetime.utcnow()
        if row.status == "closed":
            row.closed_at = row.closed_at or datetime.utcnow()
        db.session.flush()
        if commit:
            db.session.commit()
        return row


__all__ = ["BusinessReviewService"]
