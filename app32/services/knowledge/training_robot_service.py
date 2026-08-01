from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from typing import Any

from models import db
from models.knowledge import KnowledgeFeedback, KnowledgeInteraction, KnowledgeTrainingProposal


class KnowledgeTrainingRobotService:
    """Consolida feedback negativo em propostas auditáveis, sem aplicar mudanças."""

    NEGATIVE_RATINGS = {"partial", "wrong"}

    def build_proposals(
        self,
        *,
        company_id: int | None,
        min_evidence: int = 2,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = (
            db.session.query(KnowledgeFeedback, KnowledgeInteraction)
            .join(KnowledgeInteraction, KnowledgeFeedback.interaction_id == KnowledgeInteraction.id)
            .filter(KnowledgeFeedback.rating.in_(self.NEGATIVE_RATINGS))
            .order_by(KnowledgeFeedback.created_at.desc())
            .limit(limit)
        )
        if company_id is None:
            query = query.filter(KnowledgeInteraction.company_id.is_(None))
        else:
            query = query.filter(KnowledgeInteraction.company_id == int(company_id))

        buckets: dict[str, list[tuple[KnowledgeFeedback, KnowledgeInteraction]]] = defaultdict(list)
        for feedback, interaction in query.all():
            buckets[self._pattern(interaction.normalized_question)].append((feedback, interaction))

        created = []
        for pattern, items in buckets.items():
            if len(items) < min_evidence:
                continue
            if self._existing_pending(company_id=company_id, pattern=pattern):
                continue
            reasons = Counter(item[0].reason or "unspecified" for item in items)
            intents = Counter((item[1].understanding_json or {}).get("intent") or "unknown" for item in items)
            domains = Counter((item[1].understanding_json or {}).get("domain") or "general" for item in items)
            citations = []
            for _, interaction in items:
                citations.extend(
                    citation.get("source_type")
                    for citation in (interaction.citations_json or [])
                    if isinstance(citation, dict) and citation.get("source_type")
                )
            suggestion_type = self._suggestion_type(reasons)
            proposal = KnowledgeTrainingProposal(
                proposal_uuid=uuid.uuid4().hex,
                company_id=company_id,
                proposal_scope="product" if company_id is None else "company",
                pattern=pattern,
                suggested_intent=intents.most_common(1)[0][0],
                suggested_domain=domains.most_common(1)[0][0],
                suggestion_type=suggestion_type,
                evidence_count=len(items),
                evidence_json=[
                    {
                        "interaction_id": interaction.interaction_uuid,
                        "rating": feedback.rating,
                        "reason": feedback.reason,
                        "question": interaction.question,
                    }
                    for feedback, interaction in items[:10]
                ],
                sources_json=Counter(citations).most_common(10),
                recommendation_json={
                    "action": suggestion_type,
                    "reasons": reasons.most_common(),
                    "apply_automatically": False,
                },
                status="pending_review",
            )
            db.session.add(proposal)
            created.append(proposal)
        db.session.commit()
        return {"created_count": len(created), "proposals": [item.to_dict() for item in created]}

    @staticmethod
    def _pattern(normalized_question: str) -> str:
        tokens = [token for token in str(normalized_question or "").split() if len(token) > 2]
        return " ".join(tokens[:8])[:240] or "sem pergunta"

    @staticmethod
    def _suggestion_type(reasons: Counter) -> str:
        top = reasons.most_common(1)[0][0] if reasons else "unspecified"
        return {
            "wrong_subject": "intent_routing",
            "too_technical": "tone_policy",
            "missing_path": "product_help_article",
            "wrong_source": "source_ranking",
            "incomplete": "answer_completeness",
            "not_found": "knowledge_gap",
            "outdated": "content_refresh",
        }.get(top, "curation_review")

    @staticmethod
    def _existing_pending(*, company_id: int | None, pattern: str) -> bool:
        query = KnowledgeTrainingProposal.query.filter_by(
            pattern=pattern,
            status="pending_review",
        )
        if company_id is None:
            query = query.filter(KnowledgeTrainingProposal.company_id.is_(None))
        else:
            query = query.filter(KnowledgeTrainingProposal.company_id == int(company_id))
        return query.first() is not None


__all__ = ["KnowledgeTrainingRobotService"]
