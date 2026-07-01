from __future__ import annotations

from typing import Any

from models import BusinessReviewRecord, StructuralLearningLink, UrgentNeedOverlay, db
from models.urgent_business_review import STRUCTURAL_LEARNING_ACTION_VALUES, STRUCTURAL_LEARNING_TYPE_VALUES
from services.urgent_business_review_common import (
    UrgentBusinessReviewError,
    clean_text,
    normalize_choice,
    validate_canonical_links,
)


class StructuralLearningService:
    """Service tenant-safe para aprendizados estruturais derivados do Business Review."""

    @staticmethod
    def get_learning_link(company_id: int, learning_link_id: int) -> StructuralLearningLink:
        row = StructuralLearningLink.query.filter_by(id=learning_link_id, company_id=company_id).first()
        if row is None:
            raise UrgentBusinessReviewError(f"Aprendizado estrutural não encontrado: id={learning_link_id}.")
        return row

    @staticmethod
    def list_learning_links(
        *,
        company_id: int,
        business_review_id: int | None = None,
        urgent_need_id: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = StructuralLearningLink.query.filter_by(company_id=company_id)
        if business_review_id:
            query = query.filter(StructuralLearningLink.business_review_id == business_review_id)
        if urgent_need_id:
            query = query.filter(StructuralLearningLink.urgent_need_id == urgent_need_id)
        rows = query.order_by(StructuralLearningLink.updated_at.desc(), StructuralLearningLink.id.desc()).limit(limit).all()
        return [row.to_dict() for row in rows]

    @staticmethod
    def create_learning_link(
        *,
        company_id: int,
        business_review_id: int,
        urgent_need_id: int | None = None,
        target_project_id: int | None = None,
        target_project_task_id: int | None = None,
        target_process_id: int | None = None,
        target_routine_id: int | None = None,
        target_indicator_id: int | None = None,
        target_meeting_id: int | None = None,
        learning_type: str,
        action_decision: str = "recommended",
        accepted_risk_reason: str | None = None,
        recommended_change: str | None = None,
        created_project_id: int | None = None,
        created_task_id: int | None = None,
        created_by_user_id: int | None = None,
        commit: bool = True,
    ) -> StructuralLearningLink:
        review = BusinessReviewRecord.query.filter_by(id=business_review_id, company_id=company_id).first()
        if review is None:
            raise UrgentBusinessReviewError(f"Business Review não encontrado: id={business_review_id}.")

        if urgent_need_id:
            urgent_need = UrgentNeedOverlay.query.filter_by(id=urgent_need_id, company_id=company_id).first()
            if urgent_need is None:
                raise UrgentBusinessReviewError(f"Necessidade Urgente não encontrada: id={urgent_need_id}.")
        else:
            urgent_need_id = review.urgent_need_id

        validate_canonical_links(
            company_id=company_id,
            project_id=target_project_id,
            project_task_id=target_project_task_id,
            process_id=target_process_id,
            routine_id=target_routine_id,
            indicator_id=target_indicator_id,
            meeting_id=target_meeting_id,
            require_any=False,
        )
        validate_canonical_links(
            company_id=company_id,
            project_id=created_project_id,
            project_task_id=created_task_id,
            require_any=False,
        )

        normalized_action = normalize_choice(
            action_decision,
            allowed=STRUCTURAL_LEARNING_ACTION_VALUES,
            default="recommended",
            field="action_decision",
        )
        if normalized_action == "risk_accepted" and not clean_text(accepted_risk_reason):
            raise UrgentBusinessReviewError("Aceite de risco no aprendizado estrutural exige justificativa.")

        row = StructuralLearningLink(
            company_id=company_id,
            business_review_id=business_review_id,
            urgent_need_id=urgent_need_id,
            target_project_id=target_project_id,
            target_project_task_id=target_project_task_id,
            target_process_id=target_process_id,
            target_routine_id=target_routine_id,
            target_indicator_id=target_indicator_id,
            target_meeting_id=target_meeting_id,
            learning_type=normalize_choice(
                learning_type,
                allowed=STRUCTURAL_LEARNING_TYPE_VALUES,
                default="process_change",
                field="learning_type",
            ),
            action_decision=normalized_action,
            accepted_risk_reason=clean_text(accepted_risk_reason),
            recommended_change=clean_text(recommended_change),
            created_project_id=created_project_id,
            created_task_id=created_task_id,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        db.session.add(row)
        db.session.flush()
        if commit:
            db.session.commit()
        return row

    @staticmethod
    def update_action_decision(
        *,
        company_id: int,
        learning_link_id: int,
        action_decision: str,
        accepted_risk_reason: str | None = None,
        recommended_change: str | None = None,
        updated_by_user_id: int | None = None,
        commit: bool = True,
    ) -> StructuralLearningLink:
        row = StructuralLearningService.get_learning_link(company_id, learning_link_id)
        normalized_action = normalize_choice(
            action_decision,
            allowed=STRUCTURAL_LEARNING_ACTION_VALUES,
            default="recommended",
            field="action_decision",
        )
        if normalized_action == "risk_accepted" and not clean_text(accepted_risk_reason or row.accepted_risk_reason):
            raise UrgentBusinessReviewError("Aceite de risco no aprendizado estrutural exige justificativa.")
        row.action_decision = normalized_action
        if accepted_risk_reason is not None:
            row.accepted_risk_reason = clean_text(accepted_risk_reason)
        if recommended_change is not None:
            row.recommended_change = clean_text(recommended_change)
        row.updated_by_user_id = updated_by_user_id
        db.session.flush()
        if commit:
            db.session.commit()
        return row


__all__ = ["StructuralLearningService"]
