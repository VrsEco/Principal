from __future__ import annotations

import os
import inspect
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Mapping, get_type_hints

from src.intelligence.security.runtime_identity import resolve_runtime_identity
from src.intelligence.security.tool_policy import MUTATING_ACTIONS, ToolPolicyRequest, evaluate_tool_policy, require_tool_policy
from src.intelligence.tool_context import (
    reset_legacy_tool_context,
    reset_sapiens_context,
    set_legacy_tool_context,
    set_sapiens_context,
)
from src.intelligence.tooling.capabilities import infer_tool_action
from src.core.mcp_http_auth import get_http_request_context


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _coerce_optional_int_list(value: Any) -> tuple[int, ...]:
    if isinstance(value, (list, tuple, set, frozenset)):
        normalized: list[int] = []
        for item in value:
            coerced = _coerce_optional_int(item)
            if coerced is not None and coerced not in normalized:
                normalized.append(coerced)
        return tuple(normalized)
    return ()


def _coerce_exact_identity_identifier(value: Any) -> str | None:
    """Preserva issuer/sub OIDC; não aplicar trim/casefold antes do vínculo."""

    return value if isinstance(value, str) and value and value.strip() else None


def _principal_grant_gate_enabled() -> bool:
    """Ativa o gate somente após migration e provisionamento de principals."""

    value = str(os.environ.get("APP32_MCP_USE_PRINCIPAL_GRANTS", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _is_authenticated_http_context(context: Mapping[str, Any]) -> bool:
    """Indica contexto injetado pelo transporte HTTP, distinto do stdio/env."""

    transport = str(context.get("transport") or "").strip().lower()
    return transport in {"http", "sse", "streamable_http", "streamable-http"}


def _policy_requires_persisted_approval(decision: Any) -> bool:
    """Distingue a negativa de human gate de qualquer outra negativa da policy."""

    if getattr(decision, "allowed", False):
        return False
    reason = str(getattr(decision, "reason", "")).strip().lower()
    return "confirmação explícita" in reason or "human gate" in reason


def _emit_mcp_policy_audit(source: Mapping[str, Any], request: ToolPolicyRequest,
                           payload: dict[str, Any], *, allowed: bool, reason: str) -> None:
    from services.tool_approval_service import canonical_payload_digest
    from src.intelligence.audit import build_ai_execution_audit_record, emit_ai_execution_audit_event

    # Não copiar payload, prompt, token ou subject para metadata livre.
    metadata = {key: source.get(key) for key in (
        "principal_id", "subject_type", "client_id", "auth_method", "token_scopes", "correlation_id",
    ) if source.get(key) is not None}
    metadata.update({
        "surface": request.surface,
        "policy_allowed": allowed,
        "policy_reason": reason,
        "risk": request.risk,
        "payload_digest": canonical_payload_digest(payload),
        "approval_request_id": (request.metadata or {}).get("approved_human_gate_request_id"),
    })
    record = build_ai_execution_audit_record(
        event_type="mcp.tool_policy.allowed" if allowed else "mcp.tool_policy.blocked",
        runtime="mcp", status="allowed" if allowed else "blocked",
        domain=request.domain, operation=request.action, tool_name=request.tool_name,
        scope=request.surface, company_id=request.requested_company_id,
        user_id=source.get("user_id"), thread_id=source.get("thread_id"),
        trace_id=source.get("correlation_id"), metadata=metadata,
        principal_id=source.get("principal_id"), auth_method=source.get("auth_method"),
        client_id=source.get("client_id"), surface=request.surface,
        token_scopes=source.get("token_scopes") or (), policy_allowed=allowed,
        policy_reason=reason, approval_request_id=metadata["approval_request_id"],
        payload_digest=metadata["payload_digest"],
    )
    emit_ai_execution_audit_event(
        record, require_persistence=allowed and request.action in MUTATING_ACTIONS,
    )


def extract_mcp_payload(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    if kwargs:
        return dict(kwargs)
    if not args:
        return {}
    first = args[0]
    if isinstance(first, Mapping):
        return dict(first)
    return {}




def _resolve_requested_company_id(raw_payload: Mapping[str, Any], http_request_context: Mapping[str, Any]) -> tuple[int | None, str | None]:
    candidates = (
        (raw_payload.get("company_id"), "payload.company_id"),
        (raw_payload.get("active_company_id"), "payload.active_company_id"),
        (raw_payload.get("_selected_company_id"), "payload._selected_company_id"),
        (raw_payload.get("_summary_company_id"), "payload._summary_company_id"),
        (http_request_context.get("company_id"), "http.company_id"),
    )
    for value, source in candidates:
        normalized = _coerce_optional_int(value)
        if normalized is not None:
            return normalized, source
    return None, None

def _normalize_permissions(raw_permissions: Any) -> tuple[str, ...]:
    if raw_permissions is None:
        return ()
    if isinstance(raw_permissions, dict):
        normalized: list[str] = []
        for resource, actions in raw_permissions.items():
            resource_name = str(resource).strip().lower()
            if not resource_name:
                continue
            if resource_name not in normalized:
                normalized.append(resource_name)
            if isinstance(actions, str):
                action_values = [actions]
            elif isinstance(actions, (list, tuple, set, frozenset)):
                action_values = list(actions)
            elif isinstance(actions, bool):
                action_values = []
            elif actions:
                action_values = [actions]
            else:
                action_values = []
            for action in action_values:
                action_name = str(action).strip().lower()
                if not action_name:
                    continue
                permission_key = f"{resource_name}.{action_name}"
                if permission_key not in normalized:
                    normalized.append(permission_key)
        return tuple(normalized)
    if isinstance(raw_permissions, (list, tuple, set, frozenset)):
        normalized: list[str] = []
        for item in raw_permissions:
            permission = str(item).strip().lower()
            if not permission:
                continue
            resource = permission.split(".", 1)[0]
            if resource and resource not in normalized:
                normalized.append(resource)
            if permission not in normalized:
                normalized.append(permission)
        return tuple(normalized)
    return (str(raw_permissions).strip().lower(),) if str(raw_permissions).strip() else ()


def _intersect_mcp_permission_ceiling(
    app32_permissions: tuple[str, ...],
    grant_permissions: tuple[str, ...],
) -> tuple[str, ...]:
    """Aplica o teto opcional do grant sem nunca elevar o RBAC do APP32.

    ``*`` representa somente a semântica já existente do APP32 para os perfis
    cliente/administrador dentro de empresa vinculada. Não elimina nenhuma
    outra barreira MCP; se o grant declarar um teto, o curinga é reduzido aos
    átomos explicitamente permitidos.
    """

    app32 = tuple(dict.fromkeys(app32_permissions))
    ceiling = tuple(dict.fromkeys(grant_permissions))
    if not ceiling:
        return app32
    if "*" in app32:
        return ceiling
    allowed = set(app32)
    return tuple(permission for permission in ceiling if permission in allowed)


@dataclass(frozen=True)
class MCPExecutionContext:
    user_id: int | None
    company_id: int | None
    employee_id: int | None
    role: str
    channel: str
    thread_id: str | None
    accessible_company_ids: tuple[int, ...]
    permissions: tuple[str, ...]
    metadata: dict[str, Any]
    # Aditivo para não quebrar factories legadas de contexto em testes/surfaces.
    principal_id: int | None = None
    subject_type: str = "USER"
    issuer: str | None = None
    subject: str | None = None
    client_id: str | None = None
    auth_method: str | None = None
    token_scopes: tuple[str, ...] = ()
    correlation_id: str | None = None


def resolve_mcp_execution_context(payload: Mapping[str, Any] | None = None) -> MCPExecutionContext:
    raw_payload = dict(payload or {})
    http_request_context = dict(get_http_request_context() or {})
    authenticated_http_context = _is_authenticated_http_context(http_request_context)

    legacy_user_id = _coerce_optional_int(
        http_request_context.get("user_id")
        if authenticated_http_context
        else (
            http_request_context.get("user_id")
            or os.environ.get("APP32_MCP_USER_ID")
            or os.environ.get("ACTIVE_USER_ID")
        )
    )
    # Este valor vem exclusivamente do middleware HTTP autenticado. Não aceitar
    # principal_id do payload da tool evita que um cliente escolha outro grant.
    principal_id = _coerce_optional_int(http_request_context.get("principal_id"))
    requested_company_id, requested_company_source = _resolve_requested_company_id(raw_payload, http_request_context)
    principal_grant_mode = _principal_grant_gate_enabled() and principal_id is not None
    if raw_payload.get("company_ref") is not None:
        from services.mcp_company_reference_service import resolve_company_reference

        # Referência explícita prevalece sobre seleção anterior de sessão,
        # mas não pode contradizer company_id explícito no mesmo payload.
        explicit_id = _coerce_optional_int(raw_payload.get("company_id"))
        if raw_payload.get("company_id") is not None and explicit_id is None:
            raise ValueError("company_id inválido.")
        requested_company_id = resolve_company_reference(
            raw_payload["company_ref"],
            principal_id=principal_id if principal_grant_mode else None,
            user_id=legacy_user_id,
            explicit_id=explicit_id,
            accessible_company_ids=(
                _coerce_optional_int_list(http_request_context["accessible_company_ids"])
                if "accessible_company_ids" in http_request_context and not principal_grant_mode
                else None
            ),
        )
        requested_company_source = "payload.company_ref"
    channel = str(
        (http_request_context.get("channel") or "mcp_http")
        if authenticated_http_context
        else (
            raw_payload.get("channel")
            or http_request_context.get("channel")
            or os.environ.get("APP32_MCP_CHANNEL")
            or "claude_code"
        )
    ).strip().lower()
    thread_id = str(
        raw_payload.get("thread_id")
        or http_request_context.get("thread_id")
        or os.environ.get("APP32_MCP_THREAD_ID")
        or os.environ.get("APP32_MCP_SESSION_ID")
        or ""
    ).strip() or None

    runtime_identity: dict[str, Any] = {}
    user_id = legacy_user_id
    employee_id: int | None = None
    principal_grant_enforced = False

    if principal_grant_mode:
        from services.principal_authorization_service import principal_authorization_service

        grant_decision = principal_authorization_service.resolve_for_company(
            principal_id=principal_id,
            # Em modo de principal, empresa precisa ser solicitada por request
            # e autorizada pelo grant. Nunca use empresa/fallback do legado.
            company_id=requested_company_id,
        )
        if not grant_decision.allowed:
            raise PermissionError(f"principal grant negado: {grant_decision.reason}")

        # A identidade vem do principal persistido, não do token legado, env
        # do processo ou headers. SERVICE/AGENT continuam sem user sintético.
        user_id = _coerce_optional_int(getattr(grant_decision.principal, "user_id", None))
        resolved_company_id = grant_decision.company_id
        trusted_runtime_identity: dict[str, Any] = {}
        if user_id is not None:
            trusted_runtime_identity = resolve_runtime_identity(
                user_id=user_id,
                company_id=resolved_company_id,
            )
            if resolved_company_id not in _coerce_optional_int_list(
                trusted_runtime_identity.get("accessible_company_ids")
            ):
                raise PermissionError(
                    "principal grant negado: usuário APP32 sem vínculo ativo com a empresa"
                )
            employee_id = _coerce_optional_int(trusted_runtime_identity.get("employee_id"))
        accessible_company_ids = (resolved_company_id,) if resolved_company_id is not None else ()
        disable_company_fallback = True
        company_resolution_source = "principal_company_grant"
        # Para USER, APP32 é a fonte de verdade de role e permissões a cada
        # chamada. O grant OAuth apenas vincula/revoga o tenant e, quando
        # preenchido, restringe o acesso por interseção; ele jamais o amplia.
        if user_id is not None:
            role = str(trusted_runtime_identity.get("role") or "colaborador").strip().lower() or "colaborador"
            app32_permissions = _normalize_permissions(trusted_runtime_identity.get("permissions"))
            if bool(trusted_runtime_identity.get("has_full_app32_permissions")):
                app32_permissions = ("*", *app32_permissions)
            permissions = _intersect_mcp_permission_ceiling(
                app32_permissions,
                _normalize_permissions(getattr(grant_decision, "mcp_permissions", ())),
            )
        else:
            # SERVICE/AGENT não possuem RBAC humano a espelhar. Para eles o
            # grant explícito continua sendo a autoridade de permissões.
            role = str(grant_decision.role or "colaborador").strip().lower() or "colaborador"
            permissions = _normalize_permissions(getattr(grant_decision, "mcp_permissions", ()))
        principal_grant_enforced = True
    else:
        if user_id:
            runtime_identity = resolve_runtime_identity(user_id=user_id, company_id=requested_company_id)

        http_accessible_company_ids = _coerce_optional_int_list(http_request_context.get("accessible_company_ids"))
        runtime_accessible_company_ids = tuple(
            int(company_id)
            for company_id in (runtime_identity.get("accessible_company_ids") or ())
            if _coerce_optional_int(company_id) is not None
        )
        accessible_company_ids = http_accessible_company_ids or runtime_accessible_company_ids
        disable_company_fallback = bool(http_request_context.get("disable_company_fallback"))
        resolved_company_id = requested_company_id
        if resolved_company_id is None and not disable_company_fallback:
            resolved_company_id = _coerce_optional_int(runtime_identity.get("company_id"))
        company_resolution_source = requested_company_source
        if resolved_company_id is None and len(accessible_company_ids) == 1:
            resolved_company_id = int(accessible_company_ids[0])
            company_resolution_source = "runtime_identity.single_accessible_company_id"
        fallback_role = str(
            (http_request_context.get("fallback_role") or "colaborador")
            if authenticated_http_context
            else (
                http_request_context.get("fallback_role")
                or os.environ.get("APP32_MCP_FALLBACK_ROLE")
                or "colaborador"
            )
        ).strip().lower()
        role = str(runtime_identity.get("role") or fallback_role).strip().lower() or "colaborador"
        permissions = _normalize_permissions(runtime_identity.get("permissions"))
        employee_id = _coerce_optional_int(runtime_identity.get("employee_id"))

    metadata = {
        "surface": str(
            (http_request_context.get("surface") or "user")
            if authenticated_http_context
            else (http_request_context.get("surface") or os.environ.get("APP32_MCP_SURFACE") or "user")
        ).strip().lower(),
        "transport": str(http_request_context.get("transport") or "stdio").strip().lower(),
        "client": str(
            (http_request_context.get("client") or "mcp_http")
            if authenticated_http_context
            else (http_request_context.get("client") or os.environ.get("APP32_MCP_CLIENT") or "claude_code")
        ).strip().lower(),
        "company_resolution_source": company_resolution_source,
        "runtime_profile": str(http_request_context.get("runtime_profile") or "").strip().lower() or None,
        "actor_type": str(http_request_context.get("actor_type") or "").strip().lower() or None,
        "runtime_family": str(http_request_context.get("runtime_family") or "").strip().lower() or None,
        "runtime_family_label": str(http_request_context.get("runtime_family_label") or "").strip() or None,
        "harness_key": str(http_request_context.get("harness_key") or "").strip().lower() or None,
        "harness_label": str(http_request_context.get("harness_label") or "").strip() or None,
        "mcp_enabled": bool(http_request_context.get("mcp_enabled", True)),
        "training_completed": bool(http_request_context.get("training_completed", True)),
        "client_id": str(http_request_context.get("client_id") or "").strip() or None,
        "principal_id": principal_id,
        "principal_grant_enforced": principal_grant_enforced,
        "accessible_company_ids": list(accessible_company_ids),
        "multi_company": len(accessible_company_ids) > 1,
        "selection_required_for_mutations": len(accessible_company_ids) > 1 and resolved_company_id is None,
        "disable_company_fallback": disable_company_fallback or len(accessible_company_ids) > 1,
    }

    return MCPExecutionContext(
        user_id=user_id,
        principal_id=principal_id,
        company_id=resolved_company_id,
        employee_id=employee_id,
        role=role,
        channel=channel or "claude_code",
        thread_id=thread_id,
        accessible_company_ids=accessible_company_ids,
        permissions=permissions,
        metadata=metadata,
        subject_type=str(http_request_context.get("subject_type") or "USER").strip().upper() or "USER",
        issuer=_coerce_exact_identity_identifier(http_request_context.get("issuer")),
        subject=_coerce_exact_identity_identifier(http_request_context.get("subject")),
        client_id=str(http_request_context.get("client_id") or "").strip() or None,
        auth_method=str(http_request_context.get("auth_method") or "").strip().lower() or None,
        token_scopes=tuple(
            str(scope).strip()
            for scope in (http_request_context.get("token_scopes") or ())
            if str(scope).strip()
        ),
        correlation_id=str(http_request_context.get("correlation_id") or "").strip() or None,
    )


def wrap_mcp_callable(
    callback: Callable[..., Any],
    *,
    policy_surface: str | None = None,
) -> Callable[..., Any]:
    """Envolve uma tool preservando a surface efetiva da capability.

    Um conector público pode agregar tools de superfícies distintas. O nome do
    conector não é uma autorização: a policy continua sendo avaliada na
    surface da própria tool, passada exclusivamente pelo registry do servidor.
    """
    @wraps(callback)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        from app import create_app
        from src.intelligence.tool_catalog import catalog

        payload = extract_mcp_payload(args, kwargs)
        app = create_app()
        with app.app_context():
            execution_context = resolve_mcp_execution_context(payload)
            tool_name = str(
                getattr(callback, "__app32_tool_name__", None)
                or getattr(callback, "__name__", "unknown_tool")
            ).strip() or "unknown_tool"
            capability = catalog.get_tool_capability(tool_name)
            if capability is None:
                # Nenhuma inferência por nome/descrição é autorização. Toda
                # ferramenta MCP precisa de capability canônica antes de ser
                # executável, inclusive as financeiras legadas.
                raise PermissionError(f"tool MCP sem capability canônica: {tool_name}")

            action = infer_tool_action(tool_name, getattr(capability, "domain", None))
            policy_source = {
                "principal_id": getattr(execution_context, "principal_id", None),
                "subject_type": getattr(execution_context, "subject_type", "USER"),
                "issuer": getattr(execution_context, "issuer", None),
                "subject": getattr(execution_context, "subject", None),
                "client_id": getattr(execution_context, "client_id", None),
                "auth_method": getattr(execution_context, "auth_method", None),
                "token_scopes": getattr(execution_context, "token_scopes", ()),
                "correlation_id": getattr(execution_context, "correlation_id", None),
                "user_id": execution_context.user_id,
                "company_id": execution_context.company_id,
                "employee_id": execution_context.employee_id,
                "role": execution_context.role,
                "channel": execution_context.channel,
                "thread_id": execution_context.thread_id,
                "permissions": execution_context.permissions,
                "metadata": dict(execution_context.metadata or {}),
            }
            # Dados enviados pelo cliente não são uma aprovação. A primeira
            # decisão sempre começa sem confirmação e só é reavaliada depois
            # de consumir um registro persistido exatamente vinculado à ação.
            policy_request = ToolPolicyRequest(
                tool_name=tool_name,
                surface=str(policy_surface or execution_context.metadata.get("surface") or "user"),
                domain=getattr(capability, "domain", None),
                action=action,
                risk=getattr(getattr(capability, "risk", None), "value", "medium"),
                requested_company_id=execution_context.company_id,
                accessible_company_ids=execution_context.accessible_company_ids,
                required_permissions=tuple(getattr(capability, "permissions", ()) or ()),
                confirmed_mutation=False,
                required_context=tuple(getattr(capability, "required_context", ()) or ()),
                metadata=dict(execution_context.metadata or {}),
            )
            initial_decision = evaluate_tool_policy(policy_source, policy_request)
            if not initial_decision.allowed:
                _emit_mcp_policy_audit(policy_source, policy_request, payload,
                                       allowed=False, reason=initial_decision.reason)
            if _policy_requires_persisted_approval(initial_decision):
                from services.tool_approval_service import (
                    ToolApprovalBinding,
                    ToolApprovalBindingError,
                    tool_approval_request_service,
                    tool_approval_service,
                )

                try:
                    approval_binding = ToolApprovalBinding.from_execution(
                        principal_id=getattr(execution_context, "principal_id", None),
                        company_id=execution_context.company_id,
                        tool_name=tool_name,
                        payload=payload,
                        user_id=execution_context.user_id,
                    )
                except ToolApprovalBindingError as exc:
                    raise PermissionError(f"aprovação persistida indisponível: {exc}") from exc
                approval_decision = tool_approval_service.authorize_and_consume(approval_binding)
                if not approval_decision.allowed:
                    # O MCP não pode aceitar confirmação enviada pelo CLI. A
                    # primeira tentativa cria (ou reaproveita) uma aprovação
                    # persistida no APP32, vinculada ao payload exato. Após a
                    # aprovação humana, o usuário repete a mesma chamada.
                    try:
                        approval_request = tool_approval_request_service.request(
                            approval_binding,
                            reason=initial_decision.reason,
                            channel=execution_context.channel,
                            thread_id=execution_context.thread_id,
                        )
                    except Exception as exc:
                        _emit_mcp_policy_audit(
                            policy_source,
                            policy_request,
                            payload,
                            allowed=False,
                            reason="falha ao registrar aprovação humana persistida",
                        )
                        raise PermissionError("falha ao registrar aprovação humana persistida") from exc
                    _emit_mcp_policy_audit(policy_source, policy_request, payload,
                                           allowed=False,
                                           reason=(
                                               f"aprovação humana necessária: solicitação "
                                               f"#{approval_request.approval_request_id}"
                                           ))
                    raise PermissionError(
                        f"aprovação humana necessária no APP32: solicitação "
                        f"#{approval_request.approval_request_id}. "
                        "Após aprová-la, repita exatamente a mesma chamada."
                    )
                policy_request = ToolPolicyRequest(
                    **{
                        **policy_request.__dict__,
                        "confirmed_mutation": True,
                        "metadata": {
                            **dict(policy_request.metadata or {}),
                            "approved_human_gate_request_id": approval_decision.approval_request_id,
                        },
                    }
                )
            require_tool_policy(policy_source, policy_request)
            _emit_mcp_policy_audit(policy_source, policy_request, payload, allowed=True, reason="ok")
            sapiens_token = set_sapiens_context(
                user_id=execution_context.user_id,
                company_id=execution_context.company_id,
                employee_id=execution_context.employee_id,
                channel=execution_context.channel,
                thread_id=execution_context.thread_id,
                metadata=execution_context.metadata,
            )
            legacy_tokens = set_legacy_tool_context(
                user_id=execution_context.user_id,
                company_id=execution_context.company_id,
            )
            try:
                return callback(*args, **kwargs)
            finally:
                reset_legacy_tool_context(legacy_tokens)
                reset_sapiens_context(sapiens_token)

    try:
        original_signature = inspect.signature(callback)
        resolved_hints = get_type_hints(callback, globalns=getattr(callback, "__globals__", {}))
        resolved_parameters = [
            parameter.replace(
                annotation=resolved_hints.get(parameter.name, parameter.annotation),
            )
            for parameter in original_signature.parameters.values()
        ]
        _wrapped.__signature__ = original_signature.replace(  # type: ignore[attr-defined]
            parameters=resolved_parameters,
            return_annotation=resolved_hints.get("return", original_signature.return_annotation),
        )
        _wrapped.__annotations__ = {
            parameter.name: parameter.annotation
            for parameter in resolved_parameters
            if parameter.annotation is not inspect.Signature.empty
        }
        if original_signature.return_annotation is not inspect.Signature.empty:
            _wrapped.__annotations__["return"] = _wrapped.__signature__.return_annotation
    except Exception:
        pass

    return _wrapped
