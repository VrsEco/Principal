from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field


DISCOVERY_CONFIDENCE_ROUTE_SELECT = "select"
DISCOVERY_CONFIDENCE_ROUTE_AMBIGUOUS = "ambiguous"
DISCOVERY_CONFIDENCE_ROUTE_NO_MATCH = "no_match"


class WorkflowDiscoveryConfidenceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str
    selected_code: Optional[str] = None
    selected_action_key: Optional[str] = None
    candidate_codes: List[str] = Field(default_factory=list)
    candidate_count: int = 0
    top_score: int = 0
    runner_up_score: int = 0
    score_margin: int = 0
    score_ratio: float = 0.0
    reason: str = ""


class WorkflowDiscoveryConfidencePolicy:
    def __init__(
        self,
        *,
        min_top_score_for_auto_select: int = 18,
        min_score_margin_for_auto_select: int = 8,
        min_score_ratio_for_auto_select: float = 1.20,
        max_ambiguous_candidates: int = 5,
    ):
        self._min_top_score_for_auto_select = int(min_top_score_for_auto_select)
        self._min_score_margin_for_auto_select = int(min_score_margin_for_auto_select)
        self._min_score_ratio_for_auto_select = float(min_score_ratio_for_auto_select)
        self._max_ambiguous_candidates = max(2, int(max_ambiguous_candidates or 5))

    def decide(
        self,
        top_matches: Sequence[Dict[str, Any]],
    ) -> WorkflowDiscoveryConfidenceDecision:
        candidates = [dict(item) for item in (top_matches or []) if isinstance(item, dict)]
        if not candidates:
            return WorkflowDiscoveryConfidenceDecision(
                route=DISCOVERY_CONFIDENCE_ROUTE_NO_MATCH,
                reason="no_candidates",
            )

        candidate_codes = [
            str(item.get("code") or "").strip()
            for item in candidates[: self._max_ambiguous_candidates]
            if str(item.get("code") or "").strip()
        ]
        top_match = candidates[0]
        top_score = int(top_match.get("score") or 0)
        selected_code = str(top_match.get("code") or "").strip() or None
        selected_action_key = str(top_match.get("action_key") or "").strip() or None

        if len(candidates) == 1:
            if top_score < self._min_top_score_for_auto_select:
                return WorkflowDiscoveryConfidenceDecision(
                    route=DISCOVERY_CONFIDENCE_ROUTE_NO_MATCH,
                    selected_code=selected_code,
                    selected_action_key=selected_action_key,
                    candidate_codes=candidate_codes,
                    candidate_count=1,
                    top_score=top_score,
                    reason="single_candidate_below_threshold",
                )
            return WorkflowDiscoveryConfidenceDecision(
                route=DISCOVERY_CONFIDENCE_ROUTE_SELECT,
                selected_code=selected_code,
                selected_action_key=selected_action_key,
                candidate_codes=candidate_codes,
                candidate_count=1,
                top_score=top_score,
                reason="single_candidate",
            )

        runner_up = candidates[1]
        runner_up_score = int(runner_up.get("score") or 0)
        score_margin = top_score - runner_up_score
        score_ratio = (
            float(top_score) / float(runner_up_score)
            if runner_up_score > 0 else
            float(top_score)
        )

        if (
            top_score >= self._min_top_score_for_auto_select
            and (
                score_margin >= self._min_score_margin_for_auto_select
                or score_ratio >= self._min_score_ratio_for_auto_select
            )
        ):
            return WorkflowDiscoveryConfidenceDecision(
                route=DISCOVERY_CONFIDENCE_ROUTE_SELECT,
                selected_code=selected_code,
                selected_action_key=selected_action_key,
                candidate_codes=candidate_codes,
                candidate_count=len(candidates),
                top_score=top_score,
                runner_up_score=runner_up_score,
                score_margin=score_margin,
                score_ratio=round(score_ratio, 4),
                reason="clear_winner",
            )

        return WorkflowDiscoveryConfidenceDecision(
            route=DISCOVERY_CONFIDENCE_ROUTE_AMBIGUOUS,
            selected_code=selected_code,
            selected_action_key=selected_action_key,
            candidate_codes=candidate_codes,
            candidate_count=len(candidates),
            top_score=top_score,
            runner_up_score=runner_up_score,
            score_margin=score_margin,
            score_ratio=round(score_ratio, 4),
            reason="needs_disambiguation",
        )
