from __future__ import annotations

import re
from typing import Any, Callable, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from .schemas.field_collection import WorkflowRequiredField, normalize_field_key
from .session import WorkflowSessionState

FIELD_COLLECTION_ROUTE_PROMPT_MISSING = "prompt_missing"
FIELD_COLLECTION_ROUTE_READY = "ready_confirmation"


def extract_numbered_fields_from_text(
    text: str,
    missing_fields: List[Dict[str, Any]],
) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not text or not missing_fields:
        return data

    normalized_fields = WorkflowRequiredField.normalize_many(missing_fields)
    if not normalized_fields:
        return data

    pattern = re.compile(r"(?:^|[\n;])\s*(\d{1,2})\s*[:=]\s*([^\n;]+)")
    for idx_raw, value_raw in pattern.findall(text):
        try:
            pos = int(idx_raw) - 1
        except ValueError:
            continue
        if pos < 0 or pos >= len(normalized_fields):
            continue

        key = normalized_fields[pos].key
        value = value_raw.strip(" ,.")
        if key and value:
            data[key] = value

    return data


def adjust_required_fields_for_context(
    action_key: str,
    required_fields: List[WorkflowRequiredField],
) -> List[WorkflowRequiredField]:
    action = str(action_key or "").strip().lower()
    if not action.startswith("my_work."):
        return list(required_fields or [])

    return [field for field in (required_fields or []) if field.key != "empresa"]


def missing_required_fields(
    required_fields: List[WorkflowRequiredField],
    payload: Dict[str, Any],
) -> List[WorkflowRequiredField]:
    normalized_payload = {
        normalize_field_key(key): str(value).strip()
        for key, value in (payload or {}).items()
        if not str(key).startswith("_") and str(value).strip()
    }
    missing: List[WorkflowRequiredField] = []
    for field in required_fields or []:
        if field.key not in normalized_payload:
            missing.append(field)
    return missing


class FieldCollectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[WorkflowRequiredField] = Field(default_factory=list)


class FieldCollectionCoordinator:
    def __init__(
        self,
        *,
        extract_fields_from_text: Callable[[str], Dict[str, str]],
        public_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        self._extract_fields_from_text = extract_fields_from_text
        self._public_payload = public_payload

    def merge_reply_payload(
        self,
        workflow_state: WorkflowSessionState,
        *,
        text: str,
    ) -> Dict[str, Any]:
        merged = dict(workflow_state.payload or {})
        merged.update(extract_numbered_fields_from_text(text, workflow_state.missing_fields or []))
        merged.update(self._extract_fields_from_text(text))
        return self._public_payload(merged)

    def evaluate_payload(
        self,
        *,
        workflow_state: WorkflowSessionState,
        raw_required_fields: Any,
        payload: Dict[str, Any],
    ) -> FieldCollectionDecision:
        public_payload = self._public_payload(payload)
        required_fields = WorkflowRequiredField.normalize_many(raw_required_fields)
        required_fields = adjust_required_fields_for_context(
            workflow_state.workflow_action_key or "",
            required_fields,
        )
        missing_fields = missing_required_fields(required_fields, public_payload)
        if missing_fields:
            return FieldCollectionDecision(
                route=FIELD_COLLECTION_ROUTE_PROMPT_MISSING,
                payload=public_payload,
                missing_fields=missing_fields,
            )
        return FieldCollectionDecision(
            route=FIELD_COLLECTION_ROUTE_READY,
            payload=public_payload,
            missing_fields=[],
        )
