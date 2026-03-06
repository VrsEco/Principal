from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import List, Optional, Protocol, Sequence, Tuple

from .contracts import (
    WorkflowDefinition,
    WorkflowDiscoveryRequest,
    WorkflowDiscoveryResult,
    WorkflowMatch,
)
from .normalization import normalize_text, root_set, token_set, tokenize_text
from .registry import WorkflowRegistry
from .semantic_index import build_token_bigrams


def _sort_workflow_matches(matches: Sequence[WorkflowMatch]) -> List[WorkflowMatch]:
    return sorted(
        matches,
        key=lambda match: (
            -match.score,
            match.workflow.sort_order,
            match.workflow.code,
        ),
    )


def _limit_matches(matches: Sequence[WorkflowMatch], top_k: int) -> List[WorkflowMatch]:
    return list(_sort_workflow_matches(matches))[: max(1, int(top_k or 1))]


def _telemetry_summary(matches: Sequence[WorkflowMatch]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for match in matches:
        summary.append(
            {
                "code": match.workflow.code,
                "action_key": match.workflow.action_key,
                "score": match.score,
                "reasons": list(match.reasons or []),
            }
        )
    return summary


class WorkflowMatchReranker(Protocol):
    def rerank(
        self,
        request: WorkflowDiscoveryRequest,
        matches: Sequence[WorkflowMatch],
        registry: WorkflowRegistry,
    ) -> Optional[Sequence[WorkflowMatch]]:
        ...


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

        return WorkflowDiscoveryResult(
            request=request,
            matches=_limit_matches(scored_matches, request.top_k),
            telemetry={
                "strategy": "lexical",
                "normalized_text": normalized_text,
                "match_count": len(scored_matches),
                "top_matches": _telemetry_summary(_limit_matches(scored_matches, request.top_k)),
            },
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


class SemanticWorkflowMatcher:
    def discover(
        self,
        request: WorkflowDiscoveryRequest,
        registry: WorkflowRegistry,
    ) -> WorkflowDiscoveryResult:
        normalized_text = normalize_text(request.text)
        text_tokens = tokenize_text(request.text)
        text_token_set = set(text_tokens)
        text_root_set = root_set(request.text)
        text_bigrams = build_token_bigrams(text_tokens)
        scored_matches: List[WorkflowMatch] = []

        for profile in registry.semantic_index():
            score, reasons = self._score_workflow(
                normalized_text=normalized_text,
                text_tokens=text_token_set,
                text_roots=text_root_set,
                text_bigrams=text_bigrams,
                workflow_tokens=set(profile.token_set),
                workflow_roots=set(profile.root_set),
                workflow_bigrams=set(profile.bigrams),
                normalized_fragments=list(profile.normalized_fragments),
                workflow=profile.workflow,
            )
            if score <= 0:
                continue

            scored_matches.append(
                WorkflowMatch(
                    workflow=profile.workflow,
                    score=score,
                    reasons=reasons,
                )
            )

        return WorkflowDiscoveryResult(
            request=request,
            matches=_limit_matches(scored_matches, request.top_k),
            telemetry={
                "strategy": "semantic",
                "normalized_text": normalized_text,
                "match_count": len(scored_matches),
                "top_matches": _telemetry_summary(_limit_matches(scored_matches, request.top_k)),
            },
        )

    def _score_workflow(
        self,
        normalized_text: str,
        text_tokens: set[str],
        text_roots: set[str],
        text_bigrams: set[str],
        workflow_tokens: set[str],
        workflow_roots: set[str],
        workflow_bigrams: set[str],
        normalized_fragments: Sequence[str],
        workflow: WorkflowDefinition,
    ) -> Tuple[int, List[str]]:
        score = 0
        reasons: List[str] = []
        if not normalized_fragments:
            return 0, []
        best_ratio = 0.0
        best_fragment = ""

        for normalized_fragment in normalized_fragments:
            ratio = SequenceMatcher(None, normalized_text, normalized_fragment).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_fragment = normalized_fragment

        if not workflow_tokens and not workflow_roots:
            return 0, []

        root_overlap = text_roots & workflow_roots
        if root_overlap:
            request_coverage = len(root_overlap) / max(1, len(text_roots))
            workflow_coverage = len(root_overlap) / max(1, len(workflow_roots))
            score += int(round(request_coverage * 18))
            score += int(round(workflow_coverage * 14))
            reasons.append(f"semantic_roots:{','.join(sorted(root_overlap)[:6])}")

        token_overlap = text_tokens & workflow_tokens
        if token_overlap:
            score += min(8, len(token_overlap) * 2)
            reasons.append(f"semantic_tokens:{','.join(sorted(token_overlap)[:6])}")

        bigram_overlap = text_bigrams & workflow_bigrams
        if bigram_overlap:
            score += min(8, len(bigram_overlap) * 4)
            reasons.append(f"semantic_bigrams:{','.join(sorted(bigram_overlap)[:3])}")

        if best_ratio >= 0.80:
            score += 12
            reasons.append(f"semantic_similarity_high:{best_fragment}")
        elif best_ratio >= 0.65:
            score += 8
            reasons.append(f"semantic_similarity_medium:{best_fragment}")
        elif best_ratio >= 0.52:
            score += 4
            reasons.append(f"semantic_similarity_low:{best_fragment}")

        return score, reasons


class HybridWorkflowMatcher:
    def __init__(
        self,
        *,
        lexical_matcher: Optional[LexicalWorkflowMatcher] = None,
        semantic_matcher: Optional[SemanticWorkflowMatcher] = None,
        reranker: Optional[WorkflowMatchReranker] = None,
    ):
        self._lexical_matcher = lexical_matcher or LexicalWorkflowMatcher()
        self._semantic_matcher = semantic_matcher or SemanticWorkflowMatcher()
        self._reranker = reranker

    def discover(
        self,
        request: WorkflowDiscoveryRequest,
        registry: WorkflowRegistry,
    ) -> WorkflowDiscoveryResult:
        discovery_top_k = max(10, int(request.top_k or 1) * 3)
        expanded_request = request.model_copy(update={"top_k": discovery_top_k})

        lexical_matches = self._lexical_matcher.discover(
            request=expanded_request,
            registry=registry,
        )
        semantic_matches = self._semantic_matcher.discover(
            request=expanded_request,
            registry=registry,
        )

        merged_matches = self._merge_matches(lexical_matches.matches, semantic_matches.matches)
        reranked_matches = self._apply_reranker(
            request=request,
            registry=registry,
            matches=merged_matches,
        )
        limited_matches = _limit_matches(reranked_matches, request.top_k)
        selected_match = limited_matches[0] if limited_matches else None
        merged_by_code = {
            match.workflow.code: match.score
            for match in merged_matches
        }
        reranker_deltas = [
            {
                "code": match.workflow.code,
                "delta": int(match.score - merged_by_code.get(match.workflow.code, match.score)),
            }
            for match in limited_matches
        ]

        return WorkflowDiscoveryResult(
            request=request,
            matches=limited_matches,
            telemetry={
                "strategy": "hybrid",
                "lexical_match_count": len(lexical_matches.matches),
                "semantic_match_count": len(semantic_matches.matches),
                "merged_match_count": len(merged_matches),
                "reranker_applied": bool(self._reranker),
                "lexical_top_matches": _telemetry_summary(
                    _limit_matches(lexical_matches.matches, request.top_k)
                ),
                "semantic_top_matches": _telemetry_summary(
                    _limit_matches(semantic_matches.matches, request.top_k)
                ),
                "final_top_matches": _telemetry_summary(limited_matches),
                "reranker_deltas": reranker_deltas,
                "selected_code": selected_match.workflow.code if selected_match else None,
                "selected_action_key": (
                    selected_match.workflow.action_key if selected_match else None
                ),
                "selected_reasons": list(selected_match.reasons or []) if selected_match else [],
            },
        )

    def _merge_matches(
        self,
        lexical_matches: Sequence[WorkflowMatch],
        semantic_matches: Sequence[WorkflowMatch],
    ) -> List[WorkflowMatch]:
        merged: dict[str, WorkflowMatch] = {}

        for source_label, matches in (
            ("lexical", lexical_matches),
            ("semantic", semantic_matches),
        ):
            for match in matches:
                code = match.workflow.code
                score_delta = int(match.score or 0)
                reasons_delta = [
                    f"{source_label}:{reason}"
                    for reason in (match.reasons or [])
                ]
                if code not in merged:
                    merged[code] = WorkflowMatch(
                        workflow=match.workflow,
                        score=score_delta,
                        reasons=reasons_delta,
                    )
                    continue

                current = merged[code]
                current.score += score_delta
                current.reasons.extend(
                    reason
                    for reason in reasons_delta
                    if reason not in current.reasons
                )

        return _sort_workflow_matches(list(merged.values()))

    def _apply_reranker(
        self,
        *,
        request: WorkflowDiscoveryRequest,
        registry: WorkflowRegistry,
        matches: Sequence[WorkflowMatch],
    ) -> List[WorkflowMatch]:
        ordered_matches = _sort_workflow_matches(matches)
        if not self._reranker or not ordered_matches:
            return ordered_matches

        reranked = self._reranker.rerank(
            request=request,
            matches=ordered_matches,
            registry=registry,
        )
        if not reranked:
            return ordered_matches

        reranked_list = list(reranked)
        seen_codes: set[str] = set()
        final_matches: List[WorkflowMatch] = []

        for match in reranked_list:
            code = str(match.workflow.code or "").strip()
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)
            final_matches.append(match)

        for match in ordered_matches:
            code = str(match.workflow.code or "").strip()
            if code in seen_codes:
                continue
            seen_codes.add(code)
            final_matches.append(match)

        return final_matches
