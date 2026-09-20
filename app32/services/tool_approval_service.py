"""Consumo seguro de aprovações humanas persistidas para tools sensíveis.

Esta service não recebe aprovação do payload da tool. Ela valida e consome um
``AgentAction`` já aprovado, vinculado ao principal, tenant, tool e digest
canônico do payload. O consumo é único e fail-closed.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


class ToolApprovalBindingError(ValueError):
    """Binding de aprovação inválido; não deve liberar fallback de compatibilidade."""


def _normalize_json(value: Any) -> Any:
    """Aceita somente JSON estável para o digest de uma ação aprovada."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ToolApprovalBindingError("payload de aprovação contém número não finito")
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ToolApprovalBindingError("payload de aprovação possui chave não textual")
        return {key: _normalize_json(value[key]) for key in sorted(value)}
    raise ToolApprovalBindingError("payload de aprovação não é JSON canônico")


def canonical_payload_digest(payload: dict[str, Any]) -> str:
    normalized = _normalize_json(payload)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _coerce_required_positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise ToolApprovalBindingError(f"{field} inválido")
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit() and int(value.strip()) > 0:
        return int(value.strip())
    raise ToolApprovalBindingError(f"{field} obrigatório")


@dataclass(frozen=True)
class ToolApprovalBinding:
    """Fronteira imutável da ação que poderá ser executada uma única vez."""

    principal_id: int
    company_id: int
    tool_name: str
    payload_digest: str
    user_id: int | None = None

    @classmethod
    def from_execution(
        cls,
        *,
        principal_id: int | str | None,
        company_id: int | str | None,
        tool_name: str,
        payload: dict[str, Any],
        user_id: int | str | None = None,
    ) -> "ToolApprovalBinding":
        normalized_tool_name = str(tool_name or "").strip()
        if not normalized_tool_name:
            raise ToolApprovalBindingError("tool_name obrigatório")
        if not isinstance(payload, dict):
            raise ToolApprovalBindingError("payload da tool deve ser objeto JSON")
        normalized_user_id = None
        if user_id is not None:
            normalized_user_id = _coerce_required_positive_int(user_id, field="user_id")
        return cls(
            principal_id=_coerce_required_positive_int(principal_id, field="principal_id"),
            company_id=_coerce_required_positive_int(company_id, field="company_id"),
            tool_name=normalized_tool_name,
            payload_digest=canonical_payload_digest(payload),
            user_id=normalized_user_id,
        )

    @property
    def approval_key(self) -> str:
        return (
            f"mcp_tool_human_gate|{self.principal_id}|{self.company_id}|"
            f"{self.tool_name}|{self.payload_digest}"
        )


@dataclass(frozen=True)
class ToolApprovalDecision:
    allowed: bool
    reason: str
    approval_request_id: int | None = None


@dataclass(frozen=True)
class ToolApprovalRequest:
    """Pedido persistido para uma operação MCP que exige gate humano."""

    approval_request_id: int
    reused_existing: bool
    approval_key: str


def _parse_expiry(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


class ToolApprovalService:
    """Localiza e consome aprovação persistida sem confiar no cliente MCP."""

    def __init__(
        self,
        *,
        now_provider: Callable[[], datetime] = datetime.utcnow,
        approved_actions_lookup: Callable[[ToolApprovalBinding], Iterable[Any]] | None = None,
        consume_approval: Callable[[Any, ToolApprovalBinding, datetime], bool] | None = None,
    ) -> None:
        self._now_provider = now_provider
        self._approved_actions_lookup = approved_actions_lookup or self._lookup_approved_actions
        self._consume_approval = consume_approval or self._consume_approved_action

    @staticmethod
    def _lookup_approved_actions(binding: ToolApprovalBinding) -> Iterable[Any]:
        from models.agent_action import AgentAction

        query = AgentAction.query.filter(
            AgentAction.type == "workflow_approval_request",
            AgentAction.status == "approved",
            AgentAction.company_id == binding.company_id,
            AgentAction.payload["approval_key"].as_string() == binding.approval_key,
        )
        if binding.user_id is None:
            query = query.filter(AgentAction.user_id.is_(None))
        else:
            query = query.filter(AgentAction.user_id == binding.user_id)
        return query.order_by(AgentAction.resolved_at.desc(), AgentAction.id.desc()).with_for_update().limit(20).all()

    @staticmethod
    def _consume_approved_action(action: Any, binding: ToolApprovalBinding, now: datetime) -> bool:
        """Marca a aprovação como consumida na mesma transação da consulta bloqueada."""

        from models import db

        if getattr(action, "status", None) != "approved":
            return False
        payload = dict(getattr(action, "payload", None) or {})
        if payload.get("approval_key") != binding.approval_key:
            return False
        payload.update(
            {
                "approval_status": "consumed",
                "approval_consumed_at": now.isoformat(),
                "approval_consumed_for_principal_id": binding.principal_id,
            }
        )
        action.payload = payload
        action.status = "executed"
        action.executed_at = now
        db.session.commit()
        return True

    def authorize_and_consume(self, binding: ToolApprovalBinding) -> ToolApprovalDecision:
        """Retorna allow somente para aprovação vigente e consumida uma vez."""

        now = self._now_provider()
        for action in self._approved_actions_lookup(binding):
            if (
                getattr(action, "status", None) != "approved"
                or getattr(action, "type", None) != "workflow_approval_request"
                or getattr(action, "company_id", None) != binding.company_id
                or getattr(action, "user_id", None) != binding.user_id
            ):
                continue
            payload = dict(getattr(action, "payload", None) or {})
            if payload.get("created_via") != "mcp_tool_approval":
                continue
            if payload.get("approval_key") != binding.approval_key:
                continue
            if payload.get("principal_id") != binding.principal_id:
                continue
            if payload.get("action_key") != f"tool.{binding.tool_name}":
                continue
            expires_at = _parse_expiry(payload.get("approval_expires_at"))
            if expires_at is None or expires_at <= now:
                continue
            if self._consume_approval(action, binding, now):
                return ToolApprovalDecision(True, "ok", approval_request_id=getattr(action, "id", None))
            return ToolApprovalDecision(False, "aprovação já consumida ou alterada")
        return ToolApprovalDecision(False, "aprovação persistida vigente não encontrada")


tool_approval_service = ToolApprovalService()


class ToolApprovalRequestService:
    """Cria o único tipo de aprovação que ``ToolApprovalService`` consome.

    O runtime HTTP não aceita um ``human_gate_confirmed`` vindo do cliente.
    Em vez disso, ele persiste um ``AgentAction`` ligado ao principal, tenant,
    nome da tool e digest canônico do payload. A tela do APP32 aprova ou recusa
    esse mesmo registro; uma nova chamada idêntica da tool consome a aprovação
    uma única vez.
    """

    def request(
        self,
        binding: ToolApprovalBinding,
        *,
        reason: str,
        channel: str | None = None,
        thread_id: str | None = None,
    ) -> ToolApprovalRequest:
        from datetime import timedelta

        from models import db
        from models.agent_action import AgentAction
        from services.agent_action_backlog_service import ensure_backlog_task_for_action

        existing = (
            AgentAction.query.filter(
                AgentAction.type == "workflow_approval_request",
                AgentAction.status == "pending",
                AgentAction.company_id == binding.company_id,
                AgentAction.user_id == binding.user_id,
                AgentAction.payload["approval_key"].as_string() == binding.approval_key,
            )
            .order_by(AgentAction.created_at.desc(), AgentAction.id.desc())
            .first()
        )
        if existing is not None:
            return ToolApprovalRequest(
                approval_request_id=int(existing.id),
                reused_existing=True,
                approval_key=binding.approval_key,
            )

        now = datetime.utcnow()
        action = AgentAction(
            type="workflow_approval_request",
            status="pending",
            requesting_agent="mcp-versus",
            handling_agent="human_approval",
            title=f"Aprovação necessária: {binding.tool_name}",
            description=(
                "Operação MCP sensível aguardando aprovação no APP32.\n"
                f"Tool: {binding.tool_name}\nPrincipal: {binding.principal_id}\n"
                f"Empresa: {binding.company_id}\nMotivo: {reason}"
            ),
            payload={
                "created_via": "mcp_tool_approval",
                "approval_key": binding.approval_key,
                "approval_status": "pending",
                "approval_expires_at": (now + timedelta(hours=24)).isoformat(),
                "principal_id": binding.principal_id,
                "action_key": f"tool.{binding.tool_name}",
                "channel": str(channel or "mcp-versus").strip() or "mcp-versus",
                "object_code": binding.tool_name,
                "request_payload_digest": binding.payload_digest,
                "thread_id": thread_id,
                "human_gate_reason": reason,
            },
            company_id=binding.company_id,
            user_id=binding.user_id,
        )
        db.session.add(action)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        try:
            ensure_backlog_task_for_action(action, autocommit=True)
        except Exception:
            # O registro de aprovação já foi persistido e é a fronteira de
            # segurança. A projeção de backlog não pode desfazer essa garantia.
            pass
        return ToolApprovalRequest(
            approval_request_id=int(action.id),
            reused_existing=False,
            approval_key=binding.approval_key,
        )


tool_approval_request_service = ToolApprovalRequestService()
