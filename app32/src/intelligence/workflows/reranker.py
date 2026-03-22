from __future__ import annotations

import os
import re
from typing import Any, Callable, Dict, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .contracts import WorkflowDiscoveryRequest, WorkflowMatch
from .matcher import WorkflowMatchReranker
from .normalization import normalize_text, token_set
from .registry import WorkflowRegistry


RerankCallable = Callable[
    [WorkflowDiscoveryRequest, Sequence[WorkflowMatch], WorkflowRegistry],
    Optional[Sequence[WorkflowMatch]],
]

LLMRerankInvokeCallable = Callable[
    [WorkflowDiscoveryRequest, Sequence[WorkflowMatch], WorkflowRegistry],
    Any,
]


class WorkflowLLMRerankCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_code: str
    reason: str = ""


class WorkflowLLMRerankDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranked: list[WorkflowLLMRerankCandidate] = Field(default_factory=list)


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


class LLMWorkflowReranker(WorkflowMatchReranker):
    def __init__(
        self,
        *,
        invoke_llm: Optional[LLMRerankInvokeCallable] = None,
        max_candidates: int = 5,
        score_step: int = 4,
        model: Optional[str] = None,
    ):
        self._max_candidates = max(2, int(max_candidates or 5))
        self._score_step = max(2, int(score_step or 4))
        self._model = str(
            model
            or os.getenv("WORKFLOW_LLM_RERANKER_MODEL")
            or "gpt-4o-mini"
        ).strip()
        self._invoke_llm = invoke_llm or self._build_langchain_invoker()

    def rerank(
        self,
        request: WorkflowDiscoveryRequest,
        matches: Sequence[WorkflowMatch],
        registry: WorkflowRegistry,
    ) -> Optional[Sequence[WorkflowMatch]]:
        ordered_matches = list(matches or [])
        if len(ordered_matches) <= 1:
            return ordered_matches

        ranked_subset = ordered_matches[: self._max_candidates]
        try:
            raw_decision = self._invoke_llm(request, ranked_subset, registry)
            decision = self._normalize_decision(raw_decision)
        except Exception:
            return ordered_matches

        if not decision.ranked:
            return ordered_matches

        by_code = {
            match.workflow.code: match
            for match in ranked_subset
        }
        ordered_codes: list[str] = []
        reasons_by_code: Dict[str, str] = {}
        for item in decision.ranked:
            code = str(item.workflow_code or "").strip()
            if not code or code not in by_code or code in ordered_codes:
                continue
            ordered_codes.append(code)
            reasons_by_code[code] = str(item.reason or "").strip()

        if not ordered_codes:
            return ordered_matches

        base_score = max(int(match.score or 0) for match in ranked_subset) + (self._score_step * len(ranked_subset))
        reranked_subset: list[WorkflowMatch] = []
        used_codes = set()
        for index, code in enumerate(ordered_codes, start=1):
            original = by_code.get(code)
            if original is None:
                continue
            used_codes.add(code)
            new_reasons = [*original.reasons, f"llm_reranker:rank={index}"]
            llm_reason = reasons_by_code.get(code)
            if llm_reason:
                new_reasons.append(f"llm_reranker:reason={llm_reason[:120]}")
            reranked_subset.append(
                WorkflowMatch(
                    workflow=original.workflow,
                    score=base_score - ((index - 1) * self._score_step),
                    reasons=new_reasons,
                )
            )

        for fallback_match in ranked_subset:
            if fallback_match.workflow.code in used_codes:
                continue
            rank_index = len(reranked_subset) + 1
            reranked_subset.append(
                WorkflowMatch(
                    workflow=fallback_match.workflow,
                    score=base_score - ((rank_index - 1) * self._score_step),
                    reasons=[*fallback_match.reasons, f"llm_reranker:fallback_rank={rank_index}"],
                )
            )

        remaining_matches = ordered_matches[self._max_candidates :]
        return [*reranked_subset, *remaining_matches]

    def _build_langchain_invoker(self) -> LLMRerankInvokeCallable:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")
        llm = ChatOpenAI(
            model=self._model,
            temperature=0,
            api_key=api_key,
        ).with_structured_output(WorkflowLLMRerankDecision)

        def _invoke(
            request: WorkflowDiscoveryRequest,
            matches: Sequence[WorkflowMatch],
            registry: WorkflowRegistry,
        ) -> WorkflowLLMRerankDecision:
            del registry
            prompt = self._build_prompt(request=request, matches=matches)
            return llm.invoke(
                [
                    SystemMessage(content=self._system_prompt()),
                    HumanMessage(content=prompt),
                ]
            )

        return _invoke

    @staticmethod
    def _normalize_decision(raw_decision: Any) -> WorkflowLLMRerankDecision:
        if isinstance(raw_decision, WorkflowLLMRerankDecision):
            return raw_decision
        if isinstance(raw_decision, BaseModel):
            return WorkflowLLMRerankDecision.model_validate(raw_decision.model_dump())
        if isinstance(raw_decision, dict):
            return WorkflowLLMRerankDecision.model_validate(raw_decision)
        raise TypeError("Resposta do reranker LLM em formato inválido.")

    @staticmethod
    def _system_prompt() -> str:
        return (
            "Você é um reranker determinístico de workflows operacionais.\n"
            "Receberá uma intenção do usuário e uma lista FECHADA de candidatos.\n"
            "Sua tarefa é ordenar os workflows do MELHOR para o PIOR, sem inventar códigos.\n"
            "Critérios principais:\n"
            "1. aderência exata à ação pedida;\n"
            "2. período temporal citado;\n"
            "3. natureza leitura vs execução;\n"
            "4. entidade operacional envolvida (projeto, tarefa, reunião, onboarding, resumo);\n"
            "5. canal e contexto descritos.\n"
            "Retorne apenas códigos que existam na lista recebida."
        )

    def _build_prompt(
        self,
        *,
        request: WorkflowDiscoveryRequest,
        matches: Sequence[WorkflowMatch],
    ) -> str:
        lines = [
            f"INTENCAO: {request.text}",
            f"CANAL: {request.channel}",
            f"COMPANY_ID: {request.company_id if request.company_id is not None else 'none'}",
            "",
            "CANDIDATOS:",
        ]
        for match in matches:
            workflow = match.workflow
            required_fields = ", ".join(
                f"{field.key}:{field.label}"
                for field in (workflow.required_fields or [])
            ) or "-"
            keywords = ", ".join(workflow.keywords or []) or "-"
            examples = ", ".join(workflow.intent_examples or []) or "-"
            lines.extend(
                [
                    f"- code={workflow.code}",
                    f"  title={workflow.title}",
                    f"  action_key={workflow.action_key}",
                    f"  score={match.score}",
                    f"  description={workflow.description or '-'}",
                    f"  keywords={keywords}",
                    f"  intent_examples={examples}",
                    f"  required_fields={required_fields}",
                    f"  current_reasons={'; '.join(match.reasons or []) or '-'}",
                ]
            )
        return "\n".join(lines)


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

        occupancy_intent = bool({"ocupacao", "capacidade", "carga"} & tokens) or (
            {"horas", "disponiveis"} <= tokens
        )
        if occupancy_intent and action_key.startswith("summary."):
            score -= 18
            reasons.append("reranker:summary_penalty_for_occupancy")

        has_overdue_tokens = bool(
            {"vencido", "vencidos", "vencida", "vencidas", "atrasado", "atrasados", "atrasada", "atrasadas"} & tokens
        )
        has_open_tokens = bool(
            {"aberto", "abertos", "aberta", "abertas", "pendente", "pendentes"} & tokens
        )

        if has_overdue_tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.overdue",
                score=score,
                reasons=reasons,
                label="my_work=overdue",
            )

        if has_open_tokens and not has_overdue_tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.open",
                score=score,
                reasons=reasons,
                label="my_work=open",
            )
        elif has_open_tokens and has_overdue_tokens and action_key == "my_work.open":
            score -= 4
            reasons.append("reranker:my_work=open_penalty_due_to_overdue_conflict")

        if {"concluido", "concluidos", "concluida", "concluidas", "finalizado", "finalizados", "finalizada", "finalizadas"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.completed_range",
                score=score,
                reasons=reasons,
                label="my_work=completed",
            )

        if {"vencer", "vence", "vencem", "vencimento", "proximos", "proximo"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.due_range",
                score=score,
                reasons=reasons,
                label="my_work=due_range",
            )

        asks_for_work_queue = any(
            snippet in normalized_text
            for snippet in {
                "para fazer",
                "temos para fazer",
                "tenho para fazer",
                "atividades pendentes para",
                "atividade pendente para",
                "instancias pendentes para",
                "instancia pendente para",
            }
        )
        period_scoped_queue = period_hint in {"today", "week", "month"} and (
            asks_for_work_queue
            or bool({"pendente", "pendentes"} & tokens)
        )
        if period_scoped_queue:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="my_work.due_range",
                score=score + 4,
                reasons=reasons,
                label=f"my_work=period_queue:{period_hint}",
            )
            if action_key == "my_work.open":
                score -= 2
                reasons.append(f"reranker:my_work=open_period_penalty:{period_hint}")

        if occupancy_intent:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="collaborator.occupancy",
                score=score,
                reasons=reasons,
                label="collaborator=occupancy",
            )
            if action_key == "collaborator.occupancy":
                score += 26
                reasons.append("reranker:occupancy_boost")

        if {"colaborador", "usuario", "responsavel", "responsaveis"} & tokens and action_key == "collaborator.occupancy":
            score += 8
            reasons.append("reranker:collaborator_scope")

        if {"agendar", "agenda", "marcar"} & tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="meeting.schedule",
                score=score,
                reasons=reasons,
                label="meeting=schedule",
            )

        if {"iniciar", "comecar"} & tokens:
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

        if {"iniciar", "comecar"} & tokens and "onboarding" in tokens:
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="onboarding.start",
                score=score,
                reasons=reasons,
                label="onboarding=start",
            )

        if {"cadastrar", "criar", "nova", "novo"} & tokens and action_key == "project_task.create":
            score += 8
            reasons.append("reranker:task=create")

        if {"finalizar", "concluir", "concluida", "concluido", "concluidas", "concluidos", "encerrar"} & tokens and action_key in {"project_task.complete", "process_instance.complete"}:
            score += 8
            reasons.append(f"reranker:complete={action_key}")
            if re.search(r"\bids?\b", normalized_text) and action_key == "project_task.complete":
                score += 6
                reasons.append("reranker:complete=batch_ids")

        if any(snippet in normalized_text for snippet in {"dar como conclu", "dar como concluida", "dar como concluído"}):
            score, reasons = self._apply_action_hint(
                action_key=action_key,
                expected="project_task.complete",
                score=score + 4,
                reasons=reasons,
                label="task=complete_phrase",
            )

        if (
            any(snippet in normalized_text for snippet in {"coloque", "mudar", "alterar"})
            and any(snippet in normalized_text for snippet in {"para o dia", "prazo", "nova data", "novo prazo"})
            and action_key == "project_task.update"
        ):
            score += 18
            reasons.append("reranker:task=deadline_update")

        if {"aprovar", "aprovado", "aprova"} & tokens and action_key == "agent_action.approve":
            score += 18
            reasons.append("reranker:agent_action=approve")
        if {"rejeitar", "rejeitado", "recusar", "recusado"} & tokens and action_key == "agent_action.reject":
            score += 18
            reasons.append("reranker:agent_action=reject")
        if {"revalidar", "renovar"} & tokens and action_key == "agent_action.revalidate":
            score += 18
            reasons.append("reranker:agent_action=revalidate")

        pending_decision_query = any(
            snippet in normalized_text
            for snippet in {
                "aguardando minha decisao",
                "aguardando minha decisão",
                "minha decisao",
                "minha decisão",
                "solicitacoes pendentes",
                "solicitações pendentes",
            }
        )
        if pending_decision_query and action_key == "agent_action.list_pending":
            score += 24
            reasons.append("reranker:agent_action=list_pending")

        my_companies_query = (
            bool({"empresa", "empresas"} & tokens)
            and (
                "vinculad" in normalized_text
                or "tenho acesso" in normalized_text
                or "minhas empresas" in normalized_text
                or "quantas empresas" in normalized_text
            )
            and bool({"mim", "minhas", "me"} & tokens or "a mim" in normalized_text)
        )
        if my_companies_query and action_key == "company.list_accessible":
            score += 28
            reasons.append("reranker:company=list_accessible")
        elif my_companies_query and action_key.startswith("project"):
            score -= 8
            reasons.append("reranker:project_penalty_for_company_access")

        project_task_audit_query = (
            "sem responsavel" in normalized_text
            or "sem data" in normalized_text
        ) and bool({"atividade", "atividades", "tarefa", "tarefas"} & tokens)
        if project_task_audit_query and action_key == "project_task.audit":
            score += 26
            reasons.append("reranker:project_task=audit")
        elif project_task_audit_query and action_key.startswith("my_work."):
            score -= 6
            reasons.append("reranker:my_work_penalty_for_audit")

        task_tokens = {"atividade", "atividades", "tarefa", "tarefas"} & tokens
        process_tokens = {"instancia", "instancias", "processo", "processos"} & tokens
        if task_tokens:
            if action_key.startswith("my_work.") or action_key == "project_task.complete":
                score += 6
                reasons.append("reranker:entity=project_task")
            if action_key == "process_instance.complete":
                score -= 3
        if process_tokens:
            if action_key.startswith("my_work.") or action_key == "process_instance.complete":
                score += 6
                reasons.append("reranker:entity=process_instance")
            if action_key == "project_task.complete":
                score -= 3

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


def build_default_workflow_reranker() -> WorkflowMatchReranker:
    enabled = str(os.getenv("WORKFLOW_LLM_RERANKER_ENABLED") or "").strip().lower()
    if enabled in {"1", "true", "yes", "on"}:
        try:
            return LLMWorkflowReranker()
        except Exception:
            return HeuristicWorkflowReranker()
    return HeuristicWorkflowReranker()
