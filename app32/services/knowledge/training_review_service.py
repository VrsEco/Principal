from __future__ import annotations

from collections import Counter
from typing import Any

from models import db
from models.knowledge import (
    KnowledgeFeedback,
    KnowledgeInteraction,
    KnowledgeTrainingProposal,
)
from services.knowledge.training_robot_service import KnowledgeTrainingRobotService


class KnowledgeTrainingReviewError(ValueError):
    pass


class KnowledgeTrainingReviewService:
    """Esteira de curadoria humana do Sapiens, sempre tenant-safe."""

    VALID_DECISIONS = {"approved", "rejected"}
    NEGATIVE_RATINGS = {"partial", "wrong"}

    def overview(
        self,
        *,
        company_id: int | None,
        limit: int = 50,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit or 50), 100))
        negative_feedback = self._negative_feedback(company_id=company_id, limit=safe_limit)
        gaps = self._knowledge_gaps(company_id=company_id, limit=safe_limit)
        proposals = self._proposals(company_id=company_id, limit=safe_limit)

        feedback_counts = Counter(item["rating"] for item in negative_feedback)
        proposal_counts = Counter(item["status"] for item in proposals)
        return {
            "summary": {
                "negative_feedback": len(negative_feedback),
                "partial": feedback_counts.get("partial", 0),
                "wrong": feedback_counts.get("wrong", 0),
                "knowledge_gaps": len(gaps),
                "pending_proposals": proposal_counts.get("pending_review", 0),
                "approved_proposals": proposal_counts.get("approved", 0),
                "rejected_proposals": proposal_counts.get("rejected", 0),
            },
            "feedback": negative_feedback,
            "gaps": gaps,
            "proposals": proposals,
            "playbooks": self._suggested_playbooks(
                feedback=negative_feedback,
                gaps=gaps,
                proposals=proposals,
            ),
        }

    def build_proposals(
        self,
        *,
        company_id: int | None,
        min_evidence: int = 1,
        limit: int = 100,
    ) -> dict[str, Any]:
        safe_min_evidence = max(1, min(int(min_evidence or 1), 10))
        safe_limit = max(1, min(int(limit or 100), 300))
        return KnowledgeTrainingRobotService().build_proposals(
            company_id=company_id,
            min_evidence=safe_min_evidence,
            limit=safe_limit,
        )

    def decide_proposal(
        self,
        *,
        company_id: int | None,
        proposal_id: str,
        decision: str,
        user_id: int,
        note: str | None = None,
    ) -> dict[str, Any]:
        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in self.VALID_DECISIONS:
            raise KnowledgeTrainingReviewError("Decisão inválida para a proposta.")

        proposal = self._proposal_query(company_id=company_id).filter_by(
            proposal_uuid=str(proposal_id or "")
        ).first()
        if proposal is None:
            raise KnowledgeTrainingReviewError("Proposta de treinamento não encontrada.")
        if proposal.status != "pending_review":
            raise KnowledgeTrainingReviewError("A proposta já foi revisada.")

        recommendation = dict(proposal.recommendation_json or {})
        recommendation["review"] = {
            "decision": normalized_decision,
            "reviewed_by_user_id": int(user_id),
            "note": self._clean_note(note),
        }
        proposal.status = normalized_decision
        proposal.recommendation_json = recommendation
        db.session.commit()
        return {"proposal": proposal.to_dict()}

    def _negative_feedback(self, *, company_id: int | None, limit: int) -> list[dict[str, Any]]:
        query = (
            db.session.query(KnowledgeFeedback, KnowledgeInteraction)
            .join(KnowledgeInteraction, KnowledgeFeedback.interaction_id == KnowledgeInteraction.id)
            .filter(KnowledgeFeedback.rating.in_(self.NEGATIVE_RATINGS))
            .order_by(KnowledgeFeedback.created_at.desc())
            .limit(limit)
        )
        query = self._apply_interaction_company(query, company_id=company_id)
        rows = []
        for feedback, interaction in query.all():
            rows.append(
                {
                    "feedback_id": feedback.id,
                    "interaction_id": interaction.interaction_uuid,
                    "rating": feedback.rating,
                    "reason": feedback.reason,
                    "comment": feedback.comment,
                    "expected_answer": feedback.expected_answer,
                    "question": interaction.question,
                    "answer_preview": interaction.answer_preview,
                    "understanding": dict(interaction.understanding_json or {}),
                    "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
                }
            )
        return rows

    def _knowledge_gaps(self, *, company_id: int | None, limit: int) -> list[dict[str, Any]]:
        query = (
            KnowledgeInteraction.query
            .order_by(KnowledgeInteraction.created_at.desc())
            .limit(limit * 3)
        )
        query = self._apply_model_company(query, KnowledgeInteraction, company_id=company_id)
        rows = []
        for item in query.all():
            warnings = list(item.warnings_json or [])
            if "knowledge_gap" not in warnings:
                continue
            rows.append({
                "interaction_id": item.interaction_uuid,
                "question": item.question,
                "answer_preview": item.answer_preview,
                "rating_status": item.rating_status,
                "understanding": dict(item.understanding_json or {}),
                "warnings": warnings,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
            if len(rows) >= limit:
                break
        return rows

    def _proposals(self, *, company_id: int | None, limit: int) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self._proposal_query(company_id=company_id)
            .order_by(KnowledgeTrainingProposal.created_at.desc())
            .limit(limit)
            .all()
        ]

    def _proposal_query(self, *, company_id: int | None):
        return self._apply_model_company(
            KnowledgeTrainingProposal.query,
            KnowledgeTrainingProposal,
            company_id=company_id,
        )

    @staticmethod
    def _apply_interaction_company(query, *, company_id: int | None):
        if company_id is None:
            return query.filter(KnowledgeInteraction.company_id.is_(None))
        return query.filter(KnowledgeInteraction.company_id == int(company_id))

    @staticmethod
    def _apply_model_company(query, model, *, company_id: int | None):
        if company_id is None:
            return query.filter(model.company_id.is_(None))
        return query.filter(model.company_id == int(company_id))

    @staticmethod
    def _suggested_playbooks(
        *,
        feedback: list[dict[str, Any]],
        gaps: list[dict[str, Any]],
        proposals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items = []
        domains = Counter(
            (item.get("understanding") or {}).get("domain") or "general"
            for item in [*feedback, *gaps]
        )
        for domain, count in domains.most_common(5):
            items.append(
                {
                    "title": f"Playbook de uso: {domain}",
                    "reason": f"{count} evidência(s) pedem orientação mais clara.",
                    "next_step": "Criar ou melhorar artigo de ajuda com caminho de tela, filtros e exemplos.",
                }
            )
        if any(item.get("suggestion_type") == "tone_policy" for item in proposals):
            items.append(
                {
                    "title": "Padrão de linguagem simples",
                    "reason": "Há respostas percebidas como técnicas demais.",
                    "next_step": "Converter termos internos em instruções para usuário final.",
                }
            )
        return items[:6]

    @staticmethod
    def _clean_note(value: str | None) -> str | None:
        text = " ".join(str(value or "").split())
        return text[:500] if text else None


__all__ = ["KnowledgeTrainingReviewError", "KnowledgeTrainingReviewService"]
