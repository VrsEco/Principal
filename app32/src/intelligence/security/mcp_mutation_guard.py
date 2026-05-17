from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import inspect, text

from src.intelligence.audit import build_ai_execution_audit_record, emit_ai_execution_audit_event
from src.intelligence.tool_context import get_sapiens_context


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    return parsed if parsed > 0 else default


def _coerce_optional_int(value: Any) -> int | None:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return None
    return parsed if parsed > 0 else None


def _normalize_optional_text(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    return raw or None


def _parse_json_env(raw_value: str | None) -> Any:
    payload = str(raw_value or "").strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


def _get_runtime_request_metadata() -> dict[str, Any]:
    try:
        from src.core.mcp_http_auth import get_http_request_context
    except Exception:
        get_http_request_context = None  # type: ignore[assignment]

    http_context = {}
    if get_http_request_context is not None:
        try:
            http_context = dict(get_http_request_context() or {})
        except Exception:
            http_context = {}

    sapiens_identity = get_sapiens_context()
    sapiens_metadata = dict(getattr(sapiens_identity, "metadata", None) or {})
    return {
        "http": http_context,
        "sapiens": {
            "user_id": getattr(sapiens_identity, "user_id", None),
            "company_id": getattr(sapiens_identity, "company_id", None),
            "channel": getattr(sapiens_identity, "channel", None),
            "thread_id": getattr(sapiens_identity, "thread_id", None),
            "metadata": sapiens_metadata,
        },
    }


@dataclass(frozen=True)
class MutationLimitPolicy:
    profile_name: str
    create_limit: int
    update_limit: int
    delete_limit: int
    restore_limit: int
    window_hours: int
    override_reason: str | None = None
    binding_scope: str | None = None
    is_override: bool = False

    def get_limit(self, action: str) -> int:
        normalized = str(action or "").strip().lower()
        if normalized == "create":
            return self.create_limit
        if normalized == "update":
            return self.update_limit
        if normalized == "delete":
            return self.delete_limit
        if normalized == "restore":
            return self.restore_limit
        return self.update_limit


@dataclass(frozen=True)
class MutationLimitDecision:
    allowed: bool
    action: str
    count: int
    limit: int
    window_hours: int
    profile_name: str
    is_override: bool
    binding_scope: str | None
    reset_at: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "count": self.count,
            "limit": self.limit,
            "window_hours": self.window_hours,
            "profile_name": self.profile_name,
            "is_override": self.is_override,
            "binding_scope": self.binding_scope,
            "reset_at": self.reset_at,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MutationLimitContext:
    user_id: int | None
    company_id: int | None
    channel: str | None
    connector: str | None
    scenario: str | None
    role: str | None


@dataclass(frozen=True)
class MutationLimitBinding:
    profile_name: str
    user_id: int | None = None
    company_id: int | None = None
    channel: str | None = None
    connector: str | None = None
    scenario: str | None = None
    role: str | None = None
    override_reason: str | None = None

    def matches(self, context: MutationLimitContext) -> bool:
        return all(
            (
                self.user_id is None or self.user_id == context.user_id,
                self.company_id is None or self.company_id == context.company_id,
                self.channel is None or self.channel == context.channel,
                self.connector is None or self.connector == context.connector,
                self.scenario is None or self.scenario == context.scenario,
                self.role is None or self.role == context.role,
            )
        )

    def specificity(self) -> int:
        return sum(
            1
            for value in (
                self.user_id,
                self.company_id,
                self.channel,
                self.connector,
                self.scenario,
                self.role,
            )
            if value is not None
        )

    def scope_label(self) -> str:
        parts: list[str] = []
        if self.user_id is not None:
            parts.append(f"user_id={self.user_id}")
        if self.company_id is not None:
            parts.append(f"company_id={self.company_id}")
        if self.channel:
            parts.append(f"channel={self.channel}")
        if self.connector:
            parts.append(f"connector={self.connector}")
        if self.scenario:
            parts.append(f"scenario={self.scenario}")
        if self.role:
            parts.append(f"role={self.role}")
        return ", ".join(parts) or "binding genérico"


def load_mutation_limit_policy() -> MutationLimitPolicy:
    return MutationLimitPolicy(
        profile_name="default",
        create_limit=_coerce_positive_int(os.environ.get("APP32_MCP_CREATE_LIMIT"), 20),
        update_limit=_coerce_positive_int(os.environ.get("APP32_MCP_UPDATE_LIMIT"), 50),
        delete_limit=_coerce_positive_int(os.environ.get("APP32_MCP_DELETE_LIMIT"), 10),
        restore_limit=_coerce_positive_int(os.environ.get("APP32_MCP_RESTORE_LIMIT"), 10),
        window_hours=_coerce_positive_int(os.environ.get("APP32_MCP_MUTATION_WINDOW_HOURS"), 24),
    )


def _load_mutation_limit_profiles() -> dict[str, MutationLimitPolicy]:
    default_policy = load_mutation_limit_policy()
    profiles: dict[str, MutationLimitPolicy] = {"default": default_policy}
    raw_profiles = _parse_json_env(os.environ.get("APP32_MCP_MUTATION_LIMIT_PROFILES_JSON"))
    if not isinstance(raw_profiles, dict):
        return profiles

    for profile_name, payload in raw_profiles.items():
        if not isinstance(payload, dict):
            continue
        normalized_name = str(profile_name or "").strip().lower()
        if not normalized_name:
            continue
        base = profiles["default"]
        profiles[normalized_name] = MutationLimitPolicy(
            profile_name=normalized_name,
            create_limit=_coerce_positive_int(payload.get("create_limit"), base.create_limit),
            update_limit=_coerce_positive_int(payload.get("update_limit"), base.update_limit),
            delete_limit=_coerce_positive_int(payload.get("delete_limit"), base.delete_limit),
            restore_limit=_coerce_positive_int(payload.get("restore_limit"), base.restore_limit),
            window_hours=_coerce_positive_int(payload.get("window_hours"), base.window_hours),
            override_reason=str(payload.get("override_reason") or "").strip() or None,
            binding_scope=str(payload.get("binding_scope") or "").strip() or None,
            is_override=bool(payload.get("is_override", normalized_name != "default")),
        )
    return profiles


def _load_mutation_limit_bindings() -> list[MutationLimitBinding]:
    raw_bindings = _parse_json_env(os.environ.get("APP32_MCP_MUTATION_LIMIT_BINDINGS_JSON"))
    if not isinstance(raw_bindings, list):
        return []

    bindings: list[MutationLimitBinding] = []
    for item in raw_bindings:
        if not isinstance(item, dict):
            continue
        profile_name = str(item.get("profile") or item.get("profile_name") or "").strip().lower()
        if not profile_name:
            continue
        bindings.append(
            MutationLimitBinding(
                profile_name=profile_name,
                user_id=_coerce_optional_int(item.get("user_id")),
                company_id=_coerce_optional_int(item.get("company_id")),
                channel=_normalize_optional_text(item.get("channel")),
                connector=_normalize_optional_text(item.get("connector")),
                scenario=_normalize_optional_text(item.get("scenario")),
                role=_normalize_optional_text(item.get("role")),
                override_reason=str(item.get("override_reason") or "").strip() or None,
            )
        )
    return bindings


def _resolve_mutation_limit_context(*, company_id: int | None, user_id: int | None) -> MutationLimitContext:
    runtime_metadata = _get_runtime_request_metadata()
    http_context = runtime_metadata.get("http") or {}
    sapiens_context = runtime_metadata.get("sapiens") or {}
    sapiens_metadata = sapiens_context.get("metadata") or {}

    channel = (
        _normalize_optional_text(http_context.get("channel"))
        or _normalize_optional_text(sapiens_context.get("channel"))
        or _normalize_optional_text(os.environ.get("APP32_MCP_CHANNEL"))
    )
    connector = (
        _normalize_optional_text(http_context.get("client"))
        or _normalize_optional_text(sapiens_metadata.get("client"))
        or _normalize_optional_text(os.environ.get("APP32_MCP_CONNECTOR"))
        or channel
    )
    scenario = (
        _normalize_optional_text(os.environ.get("APP32_MCP_MUTATION_SCENARIO"))
        or _normalize_optional_text(http_context.get("runtime_profile"))
        or _normalize_optional_text(sapiens_metadata.get("runtime_profile"))
        or _normalize_optional_text(http_context.get("harness_key"))
        or _normalize_optional_text(sapiens_metadata.get("harness_key"))
        or _normalize_optional_text(os.environ.get("APP32_MCP_RUNTIME_PROFILE"))
        or _normalize_optional_text(os.environ.get("APP32_MCP_HARNESS_KEY"))
    )
    role = (
        _normalize_optional_text(http_context.get("fallback_role"))
        or _normalize_optional_text(os.environ.get("APP32_MCP_FALLBACK_ROLE"))
    )
    return MutationLimitContext(
        user_id=(
            _coerce_optional_int(user_id)
            or _coerce_optional_int(http_context.get("user_id"))
            or _coerce_optional_int(sapiens_context.get("user_id"))
        ),
        company_id=(
            _coerce_optional_int(company_id)
            or _coerce_optional_int(http_context.get("company_id"))
            or _coerce_optional_int(sapiens_context.get("company_id"))
        ),
        channel=channel,
        connector=connector,
        scenario=scenario,
        role=role,
    )


def resolve_mutation_limit_policy(
    *,
    company_id: int | None,
    user_id: int | None,
) -> MutationLimitPolicy:
    profiles = _load_mutation_limit_profiles()
    explicit_profile = _normalize_optional_text(os.environ.get("APP32_MCP_MUTATION_LIMIT_PROFILE"))
    if explicit_profile and explicit_profile in profiles:
        selected = profiles[explicit_profile]
        return MutationLimitPolicy(
            profile_name=selected.profile_name,
            create_limit=selected.create_limit,
            update_limit=selected.update_limit,
            delete_limit=selected.delete_limit,
            restore_limit=selected.restore_limit,
            window_hours=selected.window_hours,
            override_reason=str(os.environ.get("APP32_MCP_MUTATION_LIMIT_OVERRIDE_REASON") or selected.override_reason or "").strip() or None,
            binding_scope="env:APP32_MCP_MUTATION_LIMIT_PROFILE",
            is_override=True,
        )

    context = _resolve_mutation_limit_context(company_id=company_id, user_id=user_id)
    matched_binding: MutationLimitBinding | None = None
    for binding in sorted(_load_mutation_limit_bindings(), key=lambda item: item.specificity(), reverse=True):
        if binding.matches(context):
            matched_binding = binding
            break

    if matched_binding is None:
        return profiles["default"]

    selected = profiles.get(matched_binding.profile_name, profiles["default"])
    return MutationLimitPolicy(
        profile_name=selected.profile_name,
        create_limit=selected.create_limit,
        update_limit=selected.update_limit,
        delete_limit=selected.delete_limit,
        restore_limit=selected.restore_limit,
        window_hours=selected.window_hours,
        override_reason=matched_binding.override_reason or selected.override_reason,
        binding_scope=matched_binding.scope_label(),
        is_override=True,
    )


def _event_type_for_action(action: str) -> str:
    return f"mcp.mutation.{str(action or '').strip().lower()}.success"


def count_recent_mutations(
    *,
    action: str,
    company_id: int,
    user_id: int,
    now: datetime | None = None,
) -> int:
    from models import db

    if not company_id or not user_id:
        return 0

    policy = resolve_mutation_limit_policy(company_id=company_id, user_id=user_id)
    anchor = now or datetime.now(timezone.utc)
    since = anchor - timedelta(hours=policy.window_hours)
    table_name = "ai_mcp_audit_events"

    inspector = inspect(db.engine)
    if not inspector.has_table(table_name):
        return 0

    row = db.session.execute(
        text(
            f"""
            SELECT COUNT(*) AS total
            FROM {table_name}
            WHERE event_type = :event_type
              AND status = 'success'
              AND company_id = :company_id
              AND user_id = :user_id
              AND occurred_at >= :since
            """
        ),
        {
            "event_type": _event_type_for_action(action),
            "company_id": int(company_id),
            "user_id": int(user_id),
            "since": since,
        },
    ).scalar_one()
    return int(row or 0)


def get_mutation_window_reset_at(
    *,
    action: str,
    company_id: int,
    user_id: int,
    now: datetime | None = None,
) -> datetime | None:
    from models import db

    policy = resolve_mutation_limit_policy(company_id=company_id, user_id=user_id)
    anchor = now or datetime.now(timezone.utc)
    since = anchor - timedelta(hours=policy.window_hours)
    table_name = "ai_mcp_audit_events"

    inspector = inspect(db.engine)
    if not inspector.has_table(table_name):
        return None

    row = db.session.execute(
        text(
            f"""
            SELECT occurred_at
            FROM {table_name}
            WHERE event_type = :event_type
              AND status = 'success'
              AND company_id = :company_id
              AND user_id = :user_id
              AND occurred_at >= :since
            ORDER BY occurred_at ASC
            LIMIT 1
            """
        ),
        {
            "event_type": _event_type_for_action(action),
            "company_id": int(company_id),
            "user_id": int(user_id),
            "since": since,
        },
    ).scalar()
    if row is None:
        return None
    if row.tzinfo is None:
        row = row.replace(tzinfo=timezone.utc)
    return row + timedelta(hours=policy.window_hours)


def evaluate_mutation_limit(
    *,
    action: str,
    company_id: int | None,
    user_id: int | None,
    now: datetime | None = None,
) -> MutationLimitDecision:
    normalized_action = str(action or "").strip().lower()
    policy = resolve_mutation_limit_policy(company_id=company_id, user_id=user_id)
    limit = policy.get_limit(normalized_action)

    if not company_id or not user_id:
        return MutationLimitDecision(
            allowed=False,
            action=normalized_action,
            count=0,
            limit=limit,
            window_hours=policy.window_hours,
            profile_name=policy.profile_name,
            is_override=policy.is_override,
            binding_scope=policy.binding_scope,
            reset_at=None,
            reason="mutações MCP exigem usuário associado e company_id resolvido",
        )

    count = count_recent_mutations(
        action=normalized_action,
        company_id=int(company_id),
        user_id=int(user_id),
        now=now,
    )
    if count >= limit:
        reset_at = get_mutation_window_reset_at(
            action=normalized_action,
            company_id=int(company_id),
            user_id=int(user_id),
            now=now,
        )
        reset_at_iso = reset_at.isoformat() if reset_at else None
        scope_label = f" via perfil '{policy.profile_name}'" if policy.profile_name else ""
        reset_label = f" Próxima liberação estimada em {reset_at_iso}." if reset_at_iso else ""
        return MutationLimitDecision(
            allowed=False,
            action=normalized_action,
            count=count,
            limit=limit,
            window_hours=policy.window_hours,
            profile_name=policy.profile_name,
            is_override=policy.is_override,
            binding_scope=policy.binding_scope,
            reset_at=reset_at_iso,
            reason=(
                f"limite de mutações para '{normalized_action}' atingido: "
                f"{count}/{limit} nas últimas {policy.window_hours}h{scope_label}."
                f"{reset_label}"
            ),
        )

    return MutationLimitDecision(
        allowed=True,
        action=normalized_action,
        count=count,
        limit=limit,
        window_hours=policy.window_hours,
        profile_name=policy.profile_name,
        is_override=policy.is_override,
        binding_scope=policy.binding_scope,
        reset_at=None,
        reason="ok",
    )


def record_mutation_success(
    *,
    action: str,
    company_id: int,
    user_id: int,
    tool_name: str,
    domain: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = resolve_mutation_limit_policy(company_id=company_id, user_id=user_id)
    final_metadata = dict(metadata or {})
    final_metadata.setdefault(
        "mutation_limit_policy",
        {
            "profile_name": policy.profile_name,
            "binding_scope": policy.binding_scope,
            "is_override": policy.is_override,
            "window_hours": policy.window_hours,
            "create_limit": policy.create_limit,
            "update_limit": policy.update_limit,
            "delete_limit": policy.delete_limit,
            "restore_limit": policy.restore_limit,
            "override_reason": policy.override_reason,
        },
    )
    record = build_ai_execution_audit_record(
        event_type=_event_type_for_action(action),
        runtime="mcp",
        status="success",
        domain=domain,
        operation=action,
        tool_name=tool_name,
        scope="mcp",
        company_id=company_id,
        user_id=user_id,
        metadata=final_metadata,
    )
    return emit_ai_execution_audit_event(record)
