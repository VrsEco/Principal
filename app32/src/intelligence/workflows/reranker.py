from __future__ import annotations

import re
from typing import Callable, Optional, Sequence

from .contracts import WorkflowDiscoveryRequest, WorkflowMatch
from .matcher import WorkflowMatchReranker
from .normalization import normalize_text, token_set
from .registry import WorkflowRegistry


RerankCallable = Callable[
    [WorkflowDiscoveryRequest, Sequence[WorkflowMatch], WorkflowRegistry],
    Optional[Sequence[WorkflowMatch]],
]


class CallableWorkflowReranker(WorkflowMatchReranker):
    def __init__(self, rerank_callable: RerankCallable):
        self._rerank_callable = rerank_callable

    def rerank(
        self,
        request: WorkflowDiscoveryRequest,
        matches: Sequence[WorkflowMatch],
        registry: WorkflowRegistry,
    ) -> Optional[Sequence[WorkflowMatch]]:
        return self._rerank_callable(request, matches, registry)


class HeuristicWorkflowReranker(WorkflowMatchReranker):
    def rerank(
        self,
        request: WorkflowDiscoveryRequest,
        matches: Sequence[WorkflowMatch],
        registry: WorkflowRegistry,
    ) -> Optional[Sequence[WorkflowMatch]]:
        del registry

        normalized_text = normalize_text(request.text)
        tokens = token_set(request.text)
        if not matches:
            return list(matches)

        reranked: list[WorkflowMatch] = []
        for match in matches:
            delta, reasons = self._score_candidate(
                action_key=str(match.workflow.action_key or "").strip().lower(),
                normalized_text=normalized_text,
                tokens=tokens,
            )
            reranked.append(
                WorkflowMatch(
                    workflow=match.workflow,
                    score=match.score + delta,
                    reasons=[*match.reasons, *reasons],
                )
            )

        return sorted(
            reranked,
            key=lambda item: (
                -item.score,
                item.workflow.sort_order,
                item.workflow.code,
            ),
        )

    def _score_candidate(
        self,
        *,
        action_key: str,
        normalized_text: str,
        tokens: set[str],
    ) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        period_hint = self._resolve_period_hint(normalized_text)
        if period_hint and action_key.startswith("summary."):
            expected_action = {
                "today": "summary.today",
                "week": "summary.week",
                "month": "summary.month",
                "custom": "summary.custom",
            }.get(period_hint)
            if expected_action == action_key:
                score += 16
                reasons.append(f"reranker:summary_period={period_hint}")
            elif action_key in {"summary.today", "summary.week", "summary.month", "summary.custom"}:
                score -= 4

        if {"vencidas", "vencida", "atrasadas", "atrasada"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.overdue",
                score=score,
                reasons=reasons,
                label="my_work=overdue",
            )

        if {"abertas", "aberta", "pendentes", "pendente"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.open",
                score=score,
                reasons=reasons,
                label="my_work=open",
            )

        if {"concluidas", "concluida", "finalizadas", "finalizada"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.completed_range",
                score=score,
                reasons=reasons,
                label="my_work=completed",
            )

        if {"vencer", "vencimento", "proximos", "proximo"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.due_range",
                score=score,
                reasons=reasons,
                label="my_work=due_range",
            )

        if {"agendar", "agenda", "marcar"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="meeting.schedule",
                score=score,
                reasons=reasons,
                label="meeting=schedule",
            )

        if {"iniciar", "comecar", "comecar"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="meeting.start",
                score=score,
                reasons=reasons,
                label="meeting=start",
            )

        if {"ata", "resumir", "resumo"} & tokens and "reuniao" in tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="meeting.summarize",
                score=score,
                reasons=reasons,
                label="meeting=summarize",
            )

        if {"pronta", "pronto", "operar", "operacao", "producao"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="onboarding.go_live_check",
                score=score,
                reasons=reasons,
                label="onboarding=go_live",
            )

        if {"diagnostico", "diagnosticar", "gargalo", "pendencias"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="onboarding.diagnose",
                score=score,
                reasons=reasons,
                label="onboarding=diagnose",
            )

        if {"status", "situacao"} & tokens and "onboarding" in tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="onboarding.status",
                score=score,
                reasons=reasons,
                label="onboarding=status",
            )

        if {"iniciar", "comecar", "comecar"} & tokens and "onboarding" in tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="onboarding.start",
                score=score,
                reasons=reasons,
                label="onboarding=start",
            )

        if {"cadastrar", "criar", "nova", "novo"} & tokens:
            if action_key == "project_task.create":
                score += 8
                reasons.append("reranker:task=create")

        if {"finalizar", "concluir", "encerrar"} & tokens:
            if action_key in {"project_task.complete", "process_instance.complete"}:
                score += 8
                reasons.append(f"reranker:complete={action_key}")

        return score, reasons

    @staticmethod
    def _apply_action_hint(
        *,
        action_key: str,
        expected: str,
        score: int,
        reasons: list[str],
        label: str,
    ) -> tuple[int, list[str]]:
        if action_key == expected:
            score += 12
            reasons.append(f"reranker:{label}")
        return score, reasons

    @staticmethod
    def _resolve_period_hint(normalized_text: str) -> str | None:
        if (
            re.search(r"\b\d{2}/\d{2}/\d{4}\b", normalized_text)
            or re.search(r"\b\d{4}-\d{2}-\d{2}\b", normalized_text)
            or re.search(r"\b\d{2}\s\d{2}\s\d{4}\b", normalized_text)
            or re.search(r"\b\d{4}\s\d{2}\s\d{2}\b", normalized_text)
        ):
            return "custom"
        if "personalizado" in normalized_text or "periodo customizado" in normalized_text:
            return "custom"
        if "hoje" in normalized_text:
            return "today"
        if "semana" in normalized_text:
            return "week"
        if "mes" in normalized_text:
            return "month"
        return None
