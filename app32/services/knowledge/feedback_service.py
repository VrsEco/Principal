from __future__ import annotations

from typing import Any

from models import db
from models.knowledge import KnowledgeFeedback, KnowledgeInteraction


class KnowledgeFeedbackError(ValueError):
    pass


class KnowledgeFeedbackService:
    VALID_RATINGS = {"correct", "partial", "wrong"}
    VALID_REASONS = {
        "wrong_subject",
        "too_technical",
        "missing_path",
        "wrong_source",
        "incomplete",
        "not_found",
        "outdated",
    }
    MAX_COMMENT_LENGTH = 1000

    def register_feedback(
        self,
        *,
        interaction_id: str,
        rating: str,
        user_id: int,
        company_id: int | None,
        reason: str | None = None,
        comment: str | None = None,
        expected_answer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_rating = str(rating or "").strip().lower()
        if normalized_rating not in self.VALID_RATINGS:
            raise KnowledgeFeedbackError("Avaliação inválida para o Sapiens.")
        normalized_reason = str(reason or "").strip().lower() or None
        if normalized_reason and normalized_reason not in self.VALID_REASONS:
            raise KnowledgeFeedbackError("Motivo de feedback inválido.")
        if normalized_rating == "correct" and normalized_reason:
            raise KnowledgeFeedbackError("Resposta correta não deve receber motivo de erro.")
        cleaned_comment = self._clean_text(comment)
        cleaned_expected = self._clean_text(expected_answer)

        interaction = KnowledgeInteraction.query.filter_by(
            interaction_uuid=str(interaction_id or "")
        ).first()
        if interaction is None:
            raise KnowledgeFeedbackError("Interação de conhecimento não encontrada.")
        same_user = interaction.user_id is not None and int(interaction.user_id) == int(user_id)
        if interaction.company_id is not None and interaction.company_id != company_id and not same_user:
            raise KnowledgeFeedbackError("Feedback não pertence à empresa ativa.")

        feedback = KnowledgeFeedback(
            interaction_id=interaction.id,
            company_id=interaction.company_id,
            user_id=int(user_id),
            rating=normalized_rating,
            reason=normalized_reason,
            comment=cleaned_comment,
            expected_answer=cleaned_expected,
            metadata_json=dict(metadata or {}),
        )
        interaction.rating_status = normalized_rating
        db.session.add(feedback)
        db.session.commit()
        return {"feedback": feedback.to_dict(), "interaction": interaction.to_dict()}

    @classmethod
    def _clean_text(cls, value: str | None) -> str | None:
        text = " ".join(str(value or "").split())
        if not text:
            return None
        return text[: cls.MAX_COMMENT_LENGTH]


__all__ = ["KnowledgeFeedbackError", "KnowledgeFeedbackService"]
