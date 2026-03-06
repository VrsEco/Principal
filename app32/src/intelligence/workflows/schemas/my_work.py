from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict


class MyWorkExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    requires_period: bool = False

    @classmethod
    def build_from_action(
        cls,
        action: str,
    ) -> Tuple[Optional["MyWorkExecutionInput"], Optional[str]]:
        normalized_action = str(action or "").strip().lower()
        allowed_actions = {
            "my_work.open",
            "my_work.overdue",
            "my_work.due_range",
            "my_work.completed_range",
        }
        if normalized_action not in allowed_actions:
            return None, "Acao de consulta invalida para my_work."

        return cls(
            action=normalized_action,
            requires_period=normalized_action in {"my_work.due_range", "my_work.completed_range"},
        ), None
