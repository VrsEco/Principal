from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.intelligence.mcp_contracts import MCPErrorDetail, MCPErrorEnvelope, MCPResponseMeta, MCPSuccessEnvelope


def test_success_envelope_requires_forbid_and_serializable():
    meta = MCPResponseMeta(
        domain="work_journey",
        operation="board.read",
        scope="mcp_user",
        company_id=11,
        user_id=7,
        actor_role="colaborador",
        capability="work_journey.board.read",
        permissions=["work_journey.read"],
        generated_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )

    envelope = MCPSuccessEnvelope[dict](data={"ok": True}, meta=meta)

    assert envelope.success is True
    assert envelope.data == {"ok": True}
    assert envelope.meta.domain == "work_journey"

    with pytest.raises(ValidationError):
        MCPResponseMeta(
            domain="work_journey",
            operation="board.read",
            scope="mcp_user",
            unexpected="forbidden",  # type: ignore[arg-type]
        )


def test_error_envelope_uses_error_shape_and_forbids_extra_fields():
    meta = MCPResponseMeta(
        domain="work_journey",
        operation="agenda.move",
        scope="mcp_admin",
        company_id=11,
        user_id=1,
        actor_role="admin_tecnico",
        capability="work_journey.agenda.move",
        human_gate_required=True,
        generated_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )

    envelope = MCPErrorEnvelope(
        error=MCPErrorDetail(
            code="tenant_scope_denied",
            message="Cross-tenant access blocked.",
            details={"company_id": 11},
            retryable=False,
        ),
        meta=meta,
    )

    assert envelope.success is False
    assert envelope.error.code == "tenant_scope_denied"
    assert envelope.meta is not None

    with pytest.raises(ValidationError):
        MCPErrorDetail(
            code="invalid",
            message="ok",
            details={},
            extra_field="forbidden",  # type: ignore[arg-type]
        )
