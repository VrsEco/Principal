from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.intelligence.llm import llm_expert
from src.intelligence.tool_catalog import catalog
from services.process_execution_mode_service import get_execution_mode_catalog


class BPMNAIAssistantSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="")
    execution_mode: str = Field(default="ai_task")
    operation_type: str = Field(default="extract")
    instruction: str = Field(default="")
    model_role: str = Field(default="expert")
    tool_source: str = Field(default="mcp")
    allowed_tools: list[str] = Field(default_factory=list)
    min_confidence: float = Field(default=0.85)
    fallback_action: str = Field(default="human_review")
    allowed_decisions: list[str] = Field(default_factory=list)
    decision_routes: dict[str, str] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ProcessAIModelerAssistantService:
    TASK_OPERATION_OPTIONS = ("extract", "classify", "summarize", "validate", "enrich", "act")
    GATEWAY_OPERATION_OPTIONS = ("route", "triage", "qualify")

    @classmethod
    def build_catalog(cls) -> dict[str, Any]:
        tool_items = [
            {
                "name": tool.name,
                "description": getattr(tool, "description", "") or "",
            }
            for tool in catalog.get_langchain_tools()
        ]
        tool_items.sort(key=lambda item: item["name"])
        return {
            "task_operation_options": list(cls.TASK_OPERATION_OPTIONS),
            "gateway_operation_options": list(cls.GATEWAY_OPERATION_OPTIONS),
            "fallback_actions": ["human_review", "fail", "continue_with_warning"],
            "tool_sources": ["none", "mcp", "api"],
            "model_roles": ["expert", "router"],
            "tool_items": tool_items,
            "execution_modes": get_execution_mode_catalog(),
        }

    @classmethod
    def suggest(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = cls._normalize_payload(payload)
        heuristic = cls._fallback_suggestion(normalized)
        try:
            llm = llm_expert.with_structured_output(BPMNAIAssistantSuggestion)
            response = llm.invoke(cls._build_messages(normalized, heuristic))
            suggestion = response.model_dump() if isinstance(response, BaseModel) else dict(response or {})
        except Exception:
            suggestion = heuristic

        merged = cls._merge_with_heuristic(heuristic, suggestion)
        return {
            "ok": True,
            "suggestion": merged,
            "catalog": cls.build_catalog(),
        }

    @classmethod
    def _normalize_payload(cls, payload: dict[str, Any] | None) -> dict[str, Any]:
        data = dict(payload or {})
        semantic_type = str(data.get("semantic_type") or "").strip().lower()
        element_type = str(data.get("element_type") or "").strip()
        objective = str(data.get("objective") or "").strip()
        current_config = dict(data.get("current_config") or {})
        next_candidates = list(data.get("next_candidates") or [])
        return {
            "semantic_type": semantic_type,
            "element_type": element_type,
            "element_name": str(data.get("element_name") or "").strip(),
            "element_id": str(data.get("element_id") or "").strip(),
            "objective": objective,
            "current_config": current_config,
            "next_candidates": next_candidates,
        }

    @classmethod
    def _fallback_suggestion(cls, payload: dict[str, Any]) -> dict[str, Any]:
        semantic_type = payload["semantic_type"]
        objective = payload["objective"]
        current = payload["current_config"]
        next_candidates = payload["next_candidates"]
        if semantic_type == "ai_gateway":
            decisions = cls._infer_decisions(next_candidates)
            return {
                "summary": "Gateway assistido por IA com decisões fechadas e fallback humano.",
                "execution_mode": "ai_decision",
                "operation_type": current.get("operation_type") or "route",
                "instruction": objective or "Analise o contexto e escolha exatamente uma das rotas permitidas.",
                "model_role": current.get("model_role") or "expert",
                "tool_source": current.get("tool_source") or "none",
                "allowed_tools": list(current.get("allowed_tools") or []),
                "min_confidence": float(current.get("min_confidence") or 0.8),
                "fallback_action": current.get("fallback_action") or "human_review",
                "allowed_decisions": decisions,
                "decision_routes": {item["decision"]: item["element_id"] for item in decisions if isinstance(item, dict)},
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string"},
                        "confidence": {"type": "number"},
                        "reasoning_summary": {"type": "string"},
                    },
                },
                "notes": [
                    "Mantenha decisões críticas com fallback humano.",
                    "Prefira rotas fechadas e auditáveis.",
                ],
            }

        suggested_tools = cls._suggest_tools(objective)
        return {
            "summary": "Task de IA configurada para interpretação estruturada com schema e fallback governado.",
            "execution_mode": "ai_task",
            "operation_type": current.get("operation_type") or "extract",
            "instruction": objective or "Analise o contexto e retorne exclusivamente JSON estruturado.",
            "model_role": current.get("model_role") or "expert",
            "tool_source": current.get("tool_source") or ("mcp" if suggested_tools else "none"),
            "allowed_tools": list(current.get("allowed_tools") or suggested_tools),
            "min_confidence": float(current.get("min_confidence") or 0.85),
            "fallback_action": current.get("fallback_action") or "human_review",
            "allowed_decisions": [],
            "decision_routes": {},
            "output_schema": {
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                    "confidence": {"type": "number"},
                    "warnings": {"type": "array"},
                },
            },
            "notes": [
                "Prefira saída JSON rígida.",
                "Se usar tools MCP, mantenha allowlist mínima.",
            ],
        }

    @classmethod
    def _infer_decisions(cls, next_candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
        decisions: list[dict[str, str]] = []
        for candidate in next_candidates:
            element_id = str(candidate.get("element_id") or "").strip()
            name = str(candidate.get("element_name") or element_id).strip()
            if not element_id:
                continue
            decision = cls._slugify_decision(name)
            if not decision:
                decision = cls._slugify_decision(element_id)
            if decision and all(item["decision"] != decision for item in decisions):
                decisions.append({"decision": decision, "element_id": element_id})
        if not decisions:
            decisions = [{"decision": "human_review", "element_id": ""}]
        return decisions

    @staticmethod
    def _slugify_decision(value: str) -> str:
        text = str(value or "").strip().lower()
        text = "".join(ch if ch.isalnum() else "_" for ch in text)
        text = "_".join(filter(None, text.split("_")))
        return text[:60]

    @classmethod
    def _suggest_tools(cls, objective: str) -> list[str]:
        text = str(objective or "").lower()
        suggestions: list[str] = []
        if any(keyword in text for keyword in ("documento", "pdf", "nota", "boleto", "anexo", "arquivo")):
            suggestions.append("query_database")
        if any(keyword in text for keyword in ("fornecedor", "cliente", "cadastro")):
            suggestions.append("query_database")
        return list(dict.fromkeys(suggestions))

    @classmethod
    def _build_messages(cls, payload: dict[str, Any], heuristic: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "Você é o Sapiens especialista em modelagem BPMN/BPMS do APP32.\n"
                    "Sugira configuração fluida para AI Task ou AI Gateway.\n"
                    "Retorne somente o objeto estruturado solicitado, sem inventar tools fora do catálogo."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "payload": payload,
                        "heuristic": heuristic,
                        "tool_catalog": cls.build_catalog(),
                        "rules": [
                            "AI Task deve virar execution_mode ai_task.",
                            "AI Gateway deve virar execution_mode ai_decision.",
                            "Sempre preferir fallback human_review quando houver ambiguidade.",
                            "Allowed decisions devem casar com rotas fechadas do gateway.",
                        ],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]

    @classmethod
    def _merge_with_heuristic(cls, heuristic: dict[str, Any], suggestion: dict[str, Any]) -> dict[str, Any]:
        merged = dict(heuristic)
        merged.update({key: value for key, value in dict(suggestion or {}).items() if value not in (None, "", [], {})})
        if merged.get("execution_mode") == "ai_decision":
            allowed_decisions = merged.get("allowed_decisions") or []
            if allowed_decisions and isinstance(allowed_decisions[0], dict):
                merged["decision_routes"] = {
                    item["decision"]: item.get("element_id", "")
                    for item in allowed_decisions
                    if item.get("decision")
                }
                merged["allowed_decisions"] = [item["decision"] for item in allowed_decisions if item.get("decision")]
        return merged
