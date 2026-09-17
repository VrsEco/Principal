from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from services.tool_approval_service import (
    ToolApprovalBinding,
    ToolApprovalBindingError,
    ToolApprovalService,
    canonical_payload_digest,
)


NOW = datetime(2026, 9, 9, 12, 0, 0)


def _binding(**overrides) -> ToolApprovalBinding:
    values = {
        "principal_id": 71,
        "company_id": 9,
        "tool_name": "close_financial_period",
        "payload": {"company_id": 9, "period": "2026-09"},
        "user_id": 3,
    }
    values.update(overrides)
    return ToolApprovalBinding.from_execution(**values)


def _approval(binding: ToolApprovalBinding, **payload_overrides):
    payload = {
        "created_via": "mcp_tool_approval",
        "approval_key": binding.approval_key,
        "principal_id": binding.principal_id,
        "action_key": f"tool.{binding.tool_name}",
        "approval_expires_at": (NOW + timedelta(minutes=5)).isoformat(),
    }
    payload.update(payload_overrides)
    return SimpleNamespace(
        id=321, status="approved", type="workflow_approval_request",
        company_id=binding.company_id, user_id=binding.user_id, payload=payload,
    )


def test_approval_consumption_requires_exact_persisted_binding_and_is_single_use():
    binding = _binding()
    action = _approval(binding)
    consumed = []
    service = ToolApprovalService(
        now_provider=lambda: NOW,
        approved_actions_lookup=lambda candidate: [action],
        consume_approval=lambda candidate, expected, now: consumed.append((candidate, expected, now)) or True,
    )

    decision = service.authorize_and_consume(binding)

    assert decision.allowed is True
    assert decision.approval_request_id == 321
    assert consumed == [(action, binding, NOW)]


@pytest.mark.parametrize(
    "payload_overrides",
    [
        {"principal_id": 72},
        {"action_key": "tool.other_tool"},
        {"approval_expires_at": (NOW - timedelta(seconds=1)).isoformat()},
        {"created_via": "tool_runtime_guard"},
    ],
)
def test_approval_consumption_denies_mismatched_or_expired_persisted_records(payload_overrides):
    binding = _binding()
    action = _approval(binding, **payload_overrides)
    service = ToolApprovalService(
        now_provider=lambda: NOW,
        approved_actions_lookup=lambda candidate: [action],
        consume_approval=lambda *args: pytest.fail("aprovação inválida não pode ser consumida"),
    )

    decision = service.authorize_and_consume(binding)

    assert decision.allowed is False
    assert decision.reason == "aprovação persistida vigente não encontrada"


def test_binding_requires_principal_tenant_and_canonical_json_payload():
    with pytest.raises(ToolApprovalBindingError, match="principal_id obrigatório"):
        _binding(principal_id=None)
    with pytest.raises(ToolApprovalBindingError, match="JSON canônico"):
        _binding(payload={"unsupported": object()})

    assert canonical_payload_digest({"a": 1, "b": [True, None]}) == canonical_payload_digest(
        {"b": [True, None], "a": 1}
    )


@pytest.mark.parametrize("field,value", [
    ("company_id", 10), ("user_id", 4), ("status", "executed"),
    ("status", "rejected"), ("type", "technical_fix"),
])
def test_approval_service_defensively_rechecks_record_scope(field, value):
    binding = _binding()
    action = _approval(binding)
    setattr(action, field, value)
    service = ToolApprovalService(
        now_provider=lambda: NOW,
        approved_actions_lookup=lambda candidate: [action],
        consume_approval=lambda *args: pytest.fail("registro fora do escopo não pode ser consumido"),
    )
    assert service.authorize_and_consume(binding).allowed is False
