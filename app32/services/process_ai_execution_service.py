from __future__ import annotations

from typing import Any


AI_EXECUTION_MODES = {"ai_task", "ai_decision"}
AI_ALLOWED_MODEL_ROLES = {"router", "expert"}
AI_ALLOWED_RESPONSE_MODES = {"structured_json", "structured_text"}
AI_ALLOWED_TOOL_SOURCES = {"none", "mcp", "api"}


def is_ai_execution_mode(execution_mode: str | None) -> bool:
    return str(execution_mode or "").strip().lower() in AI_EXECUTION_MODES


def normalize_ai_contract_config(
    value: dict[str, Any] | None,
    *,
    execution_mode: str | None = None,
) -> dict[str, Any]:
    mode = str(execution_mode or "").strip().lower()
    raw = dict(value or {})

    if not raw and mode not in AI_EXECUTION_MODES:
        return {}

    instruction = str(raw.get("instruction") or raw.get("prompt") or "").strip()
    if mode in AI_EXECUTION_MODES and not instruction:
        raise ValueError("Configuração de IA exige instruction quando execution_mode for ai_task ou ai_decision.")

    model_role = str(raw.get("model_role") or "expert").strip().lower()
    if model_role not in AI_ALLOWED_MODEL_ROLES:
        raise ValueError("model_role da IA deve ser router ou expert.")

    response_mode = str(raw.get("response_mode") or "structured_json").strip().lower()
    if response_mode not in AI_ALLOWED_RESPONSE_MODES:
        raise ValueError("response_mode da IA deve ser structured_json ou structured_text.")

    tool_source = str(raw.get("tool_source") or ("mcp" if raw.get("allowed_tools") else "none")).strip().lower()
    if tool_source not in AI_ALLOWED_TOOL_SOURCES:
        raise ValueError("tool_source da IA deve ser none, mcp ou api.")

    normalized: dict[str, Any] = {
        "instruction": instruction,
        "model_role": model_role,
        "response_mode": response_mode,
        "tool_source": tool_source,
        "include_runtime_context": bool(raw.get("include_runtime_context", True)),
        "include_execution_history": bool(raw.get("include_execution_history", True)),
        "temperature": _coerce_temperature(raw.get("temperature")),
        "min_confidence": _coerce_confidence(raw.get("min_confidence")),
        "fallback_action": _normalize_optional_text(raw.get("fallback_action")) or "human_review",
        "capability_key": _normalize_optional_text(raw.get("capability_key")),
        "system_hint": _normalize_optional_text(raw.get("system_hint")),
        "allowed_tools": _normalize_string_list(raw.get("allowed_tools")),
        "input_mapping": _normalize_dict(raw.get("input_mapping")),
        "output_mapping": _normalize_dict(raw.get("output_mapping")),
        "metadata": _normalize_dict(raw.get("metadata")),
    }

    if mode == "ai_decision":
        allowed_decisions = _normalize_string_list(raw.get("allowed_decisions"))
        if not allowed_decisions:
            raise ValueError("Configuração ai_decision exige allowed_decisions com pelo menos uma opção.")
        normalized["allowed_decisions"] = allowed_decisions
    else:
        normalized["allowed_decisions"] = []

    output_schema = raw.get("output_schema")
    if output_schema is not None and not isinstance(output_schema, dict):
        raise ValueError("output_schema da IA deve ser um objeto JSON.")
    normalized["output_schema"] = dict(output_schema or {})
    return normalized


def summarize_ai_contract_config(value: dict[str, Any] | None) -> dict[str, Any]:
    config = dict(value or {})
    return {
        "model_role": config.get("model_role"),
        "response_mode": config.get("response_mode"),
        "tool_source": config.get("tool_source"),
        "min_confidence": config.get("min_confidence"),
        "fallback_action": config.get("fallback_action"),
        "allowed_tools": list(config.get("allowed_tools") or []),
        "allowed_decisions": list(config.get("allowed_decisions") or []),
        "has_output_schema": bool(config.get("output_schema")),
    }


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_string_list(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("Lista textual inválida na configuração de IA.")

    output: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in output:
            output.append(text)
    return output


def _normalize_dict(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError("Estrutura JSON inválida na configuração de IA.")
    return dict(value)


def _coerce_temperature(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("temperature da IA deve ser numérico.") from exc
    if number < 0 or number > 2:
        raise ValueError("temperature da IA deve ficar entre 0 e 2.")
    return number


def _coerce_confidence(value: Any) -> float:
    if value in (None, ""):
        return 0.8
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("min_confidence da IA deve ser numérico.") from exc
    if number < 0 or number > 1:
        raise ValueError("min_confidence da IA deve ficar entre 0 e 1.")
    return number
