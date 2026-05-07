from __future__ import annotations

from typing import Any

from services.process_execution_mode_service import normalize_execution_mode


def build_executor_descriptor(
    *,
    execution_mode: str | None,
    ui_schema_json: dict[str, Any] | None = None,
    rest_config_json: dict[str, Any] | None = None,
    mcp_config_json: dict[str, Any] | None = None,
    ai_config_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = normalize_execution_mode(execution_mode)
    descriptor = {
        "execution_mode": mode,
        "requires_user_interaction": mode in {"human_task", "open_form", "open_app32_page", "manual_external"},
        "supports_auto_run": mode in {"automatic", "api_task", "mcp_task", "ai_task", "ai_decision"},
        "executor_key": {
            "human_task": "human",
            "manual_external": "manual",
            "automatic": "automatic",
            "open_form": "ui_form",
            "open_app32_page": "ui_page",
            "api_task": "api",
            "mcp_task": "mcp",
            "ai_task": "ai",
            "ai_decision": "ai",
        }[mode],
        "config": {},
    }
    if mode in {"open_form", "open_app32_page", "human_task"}:
        descriptor["config"] = dict(ui_schema_json or {})
    elif mode == "api_task":
        descriptor["config"] = dict(rest_config_json or {})
    elif mode == "mcp_task":
        descriptor["config"] = dict(mcp_config_json or {})
    elif mode in {"ai_task", "ai_decision"}:
        descriptor["config"] = dict(ai_config_json or {})
    return descriptor
