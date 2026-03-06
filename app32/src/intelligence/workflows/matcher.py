from __future__ import annotations

import re
from typing import List, Tuple

from .contracts import (
    WorkflowDefinition,
    WorkflowDiscoveryRequest,
    WorkflowDiscoveryResult,
    WorkflowMatch,
)
from .normalization import normalize_text, token_set
from .registry import WorkflowRegistry


class LexicalWorkflowMatcher:
    def discover(
        self,
        request: WorkflowDiscoveryRequest,
        registry: WorkflowRegistry,
    ) -> WorkflowDiscoveryResult:
        normalized_text = normalize_text(request.text)
        text_tokens = token_set(request.text)
        scored_matches: List[WorkflowMatch] = []

        for workflow in registry:
            score, reasons = self._score_workflow(
                workflow=workflow,
                normalized_text=normalized_text,
                text_tokens=text_tokens,
            )
            if score <= 0:
                continue

            scored_matches.append(
                WorkflowMatch(
                    workflow=workflow,
                    score=score,
                    reasons=reasons,
                )
            )

        scored_matches.sort(
            key=lambda match: (
                -match.score,
                match.workflow.sort_order,
                match.workflow.code,
            )
        )

        return WorkflowDiscoveryResult(
            request=request,
            matches=scored_matches[: max(1, request.top_k)],
        )

    def match_menu_options(
        self,
        text: str,
        registry: WorkflowRegistry,
        top_k: int = 10,
    ) -> List[WorkflowMatch]:
        request = WorkflowDiscoveryRequest(text=text, top_k=top_k)
        result = self.discover(request=request, registry=registry)
        return result.matches

    def _score_workflow(
        self,
        workflow: WorkflowDefinition,
        normalized_text: str,
        text_tokens: set[str],
    ) -> Tuple[int, List[str]]:
        score = 0
        reasons: List[str] = []

        if workflow.code and re.search(rf"(?<!\d){re.escape(workflow.code)}(?!\d)", normalized_text):
            score += 50
            reasons.append(f"code:{workflow.code}")

        title_score, title_reasons = self._score_phrase(
            candidate=workflow.title,
            normalized_text=normalized_text,
            text_tokens=text_tokens,
            label="title",
            phrase_weight=6,
            token_weight=2,
        )
        score += title_score
        reasons.extend(title_reasons)

        for keyword in workflow.keywords:
            keyword_score, keyword_reasons = self._score_phrase(
                candidate=keyword,
                normalized_text=normalized_text,
                text_tokens=text_tokens,
                label="keyword",
                phrase_weight=8,
                token_weight=3,
            )
            score += keyword_score
            reasons.extend(keyword_reasons)

        action_key_score, action_key_reasons = self._score_phrase(
            candidate=workflow.action_key.replace(".", " ").replace("_", " "),
            normalized_text=normalized_text,
            text_tokens=text_tokens,
            label="action",
            phrase_weight=4,
            token_weight=1,
        )
        score += action_key_score
        reasons.extend(action_key_reasons)

        return score, reasons

    @staticmethod
    def _score_phrase(
        candidate: str,
        normalized_text: str,
        text_tokens: set[str],
        label: str,
        phrase_weight: int,
        token_weight: int,
    ) -> Tuple[int, List[str]]:
        candidate_normalized = normalize_text(candidate)
        if not candidate_normalized:
            return 0, []

        candidate_tokens = token_set(candidate)
        if not candidate_tokens:
            return 0, []

        score = 0
        reasons: List[str] = []

        if candidate_normalized == normalized_text:
            score += phrase_weight + 4
            reasons.append(f"{label}_exact:{candidate_normalized}")
            return score, reasons

        if candidate_normalized in normalized_text:
            score += phrase_weight
            reasons.append(f"{label}_phrase:{candidate_normalized}")

        overlap = candidate_tokens & text_tokens
        if overlap:
            if overlap == candidate_tokens:
                score += token_weight + len(overlap)
                reasons.append(f"{label}_all_tokens:{','.join(sorted(overlap))}")
            elif len(overlap) >= 2:
                score += token_weight + len(overlap) - 1
                reasons.append(f"{label}_partial_tokens:{','.join(sorted(overlap))}")

        return score, reasons
