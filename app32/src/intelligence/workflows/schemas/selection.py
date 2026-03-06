from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssistedSelectionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selection_action: str = ""
    selection_kind: str = ""
    selection_field_key: str = ""
    selection_value_key: str = "code"
    choices: List[Dict[str, Any]] = Field(default_factory=list)
    scope_label: Optional[str] = None
    item_label_plural: Optional[str] = None

    @classmethod
    def build_from_payload(cls, payload: Dict[str, Any]) -> "AssistedSelectionContext":
        return cls(
            selection_action=str(payload.get("_selection_action") or "").strip().lower(),
            selection_kind=str(payload.get("_selection_kind") or "").strip().lower(),
            selection_field_key=str(payload.get("_selection_field_key") or "").strip().lower(),
            selection_value_key=str(payload.get("_selection_value_key") or "code").strip() or "code",
            choices=list(payload.get("_choices") or []),
            scope_label=(
                str(payload.get("_scope_label")).strip()
                if payload.get("_scope_label") is not None
                else None
            ),
            item_label_plural=(
                str(payload.get("_item_label_plural")).strip()
                if payload.get("_item_label_plural") is not None
                else None
            ),
        )
