from __future__ import annotations

import inspect
from contextlib import nullcontext
from typing import Optional
from types import SimpleNamespace

import pytest
from starlette.requests import Request

import src.core.mcp_http_auth as auth
from src.core.mcp_http_auth import App32McpHttpIdentity, reset_http_request_context, set_http_request_context
from src.core.mcp_runtime import resolve_mcp_execution_context, wrap_mcp_callable


def test_runtime_prefers_http_request_context(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-1",
            user_id=3,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "company_id": 9,
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
            "runtime_profile": "squad_cliente",
            "actor_type": "client_agent",
            "harness_key": "harness_coordenador_cliente_v1",
            "harness_label": "Harness Coordenador do Squad Cliente",
            "mcp_enabled": True,
            "training_completed": True,
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [company_id],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.user_id == 3
    assert context.company_id == 9
    assert context.employee_id == 23
    assert context.role == "director"
    assert context.permissions == ("approve",)
    assert context.metadata["surface"] == "user"
    assert context.metadata["transport"] == "streamable_http"
    assert context.metadata["runtime_profile"] == "squad_cliente"
    assert context.metadata["actor_type"] == "client_agent"
    assert context.metadata["harness_key"] == "harness_coordenador_cliente_v1"
    assert context.metadata["harness_label"] == "Harness Coordenador do Squad Cliente"
    assert context.metadata["mcp_enabled"] is True
    assert context.metadata["training_completed"] is True


def test_runtime_propagates_authenticated_identity_contract_without_subject_in_metadata(monkeypatch):
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": None,
            "role": "colaborador",
            "permissions": {},
            "accessible_company_ids": [company_id],
        },
    )
    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="identity-contract",
            user_id=3,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
            principal_id=71,
            subject_type="SERVICE",
            issuer="https://auth.gestaoversus.com.br/realms/versus",
            subject="service:erp-bomix",
            auth_method="client_credentials",
            scopes=("mcp:access", "routine:read"),
            client_id="erp-bomix",
            metadata={"correlation_id": "req-71"},
        ),
        {
            "user_id": 3,
            "company_id": 9,
            "principal_id": 71,
            "subject_type": "SERVICE",
            "issuer": " https://auth.gestaoversus.com.br/realms/versus ",
            "subject": " service:erp-bomix ",
            "auth_method": "client_credentials",
            "token_scopes": ["mcp:access", "routine:read"],
            "client_id": "erp-bomix",
            "correlation_id": "req-71",
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.principal_id == 71
    assert context.subject_type == "SERVICE"
    assert context.issuer == " https://auth.gestaoversus.com.br/realms/versus "
    assert context.subject == " service:erp-bomix "
    assert context.client_id == "erp-bomix"
    assert context.auth_method == "client_credentials"
    assert context.token_scopes == ("mcp:access", "routine:read")
    assert context.correlation_id == "req-71"
    assert "subject" not in context.metadata
    assert "token_subject" not in context.metadata



def test_runtime_enforces_server_side_principal_grant_when_feature_flag_enabled(monkeypatch):
    class _GrantDecision:
        allowed = True
        company_id = 9
        role = "cliente"
        principal = type("Principal", (), {"user_id": 44})()

    class _PrincipalAuthorizationService:
        calls = []

        def resolve_for_company(self, *, principal_id, company_id):
            self.calls.append((principal_id, company_id))
            return _GrantDecision()

    principal_service = _PrincipalAuthorizationService()
    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        principal_service,
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "administrador",
            "permissions": {"finance": ["write"]},
            "accessible_company_ids": [company_id],
        },
    )
    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-principal",
            user_id=3,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
            principal_id=71,
        ),
        {"user_id": 3, "company_id": 9, "principal_id": 71, "fallback_role": "colaborador", "surface": "user"},
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert principal_service.calls == [(71, 9)]
    assert context.principal_id == 71
    assert context.user_id == 44
    assert context.employee_id == 23
    assert context.company_id == 9
    assert context.role == "cliente"
    assert context.permissions == ()
    assert context.metadata["principal_id"] == 71
    assert context.metadata["principal_grant_enforced"] is True
    assert context.metadata["company_resolution_source"] == "principal_company_grant"


def test_runtime_principal_grant_mode_never_inherits_legacy_user_or_permissions(monkeypatch):
    class _GrantDecision:
        allowed = True
        company_id = 9
        role = "cliente"
        principal = type("Principal", (), {"user_id": None})()

    class _PrincipalAuthorizationService:
        def resolve_for_company(self, *, principal_id, company_id):
            assert (principal_id, company_id) == (71, 9)
            return _GrantDecision()

    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setenv("APP32_MCP_USER_ID", "999")
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        _PrincipalAuthorizationService(),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda **kwargs: pytest.fail(f"runtime legado não deve ser resolvido: {kwargs}"),
    )
    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-technical-principal",
            user_id=3,
            company_id=9,
            fallback_role="administrador",
            allowed_surfaces=("admin",),
            principal_id=71,
        ),
        {
            "user_id": 3,
            "company_id": 9,
            "principal_id": 71,
            "fallback_role": "administrador",
            "surface": "admin",
            "transport": "streamable_http",
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.user_id is None
    assert context.employee_id is None
    assert context.role == "cliente"
    assert context.permissions == ()
    assert context.company_id == 9


def test_runtime_never_reads_principal_id_from_tool_payload(monkeypatch):
    class _UnexpectedPrincipalAuthorizationService:
        def resolve_for_company(self, **kwargs):  # pragma: no cover - não deve ser chamado
            raise AssertionError(f"gate não deveria executar: {kwargs}")

    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        _UnexpectedPrincipalAuthorizationService(),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "colaborador",
            "permissions": {},
            "accessible_company_ids": [company_id],
        },
    )
    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-no-principal",
            user_id=3,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {"user_id": 3, "company_id": 9, "fallback_role": "colaborador", "surface": "user"},
    )

    try:
        context = resolve_mcp_execution_context({"principal_id": 999})
    finally:
        reset_http_request_context(tokens)

    assert context.principal_id is None
    assert context.metadata["principal_id"] is None
    assert context.metadata["principal_grant_enforced"] is False


def test_runtime_denies_when_trusted_principal_has_no_grant(monkeypatch):
    class _GrantDecision:
        allowed = False
        reason = "grant do principal para a empresa não encontrado"

    class _PrincipalAuthorizationService:
        def resolve_for_company(self, **kwargs):
            return _GrantDecision()

    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        _PrincipalAuthorizationService(),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": None,
            "role": "colaborador",
            "permissions": {},
            "accessible_company_ids": [company_id] if company_id else [],
        },
    )
    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-denied-principal",
            user_id=None,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
            principal_id=71,
        ),
        {"company_id": 9, "principal_id": 71, "fallback_role": "colaborador", "surface": "user"},
    )

    try:
        with pytest.raises(PermissionError, match="principal grant negado"):
            resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)


def test_runtime_pins_single_accessible_company_when_request_has_no_company(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-2",
            user_id=3,
            company_id=None,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [12],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.company_id == 12
    assert context.metadata["company_resolution_source"] == "runtime_identity.single_accessible_company_id"


def test_runtime_preserves_unselected_company_when_http_context_requires_selection(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-2b",
            user_id=3,
            company_id=None,
            fallback_role="administrador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "fallback_role": "administrador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
            "accessible_company_ids": [1, 10],
            "multi_company": True,
            "disable_company_fallback": True,
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": 10,
            "employee_id": 37,
            "role": "administrator",
            "permissions": {"approve": True},
            "accessible_company_ids": [10],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.user_id == 3
    assert context.company_id is None
    assert context.employee_id == 37
    assert context.metadata["accessible_company_ids"] == [1, 10]
    assert context.metadata["selection_required_for_mutations"] is True
    assert context.metadata["disable_company_fallback"] is True


def test_runtime_prefers_selected_company_from_payload(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-3",
            user_id=3,
            company_id=None,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 3,
            "fallback_role": "colaborador",
            "surface": "user",
            "transport": "streamable_http",
            "client": "claude_remote_connector",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [12, 15],
        },
    )

    try:
        context = resolve_mcp_execution_context({"_selected_company_id": 15})
    finally:
        reset_http_request_context(tokens)

    assert context.company_id == 15
    assert context.metadata["company_resolution_source"] == "payload._selected_company_id"


def test_runtime_ignores_company_id_from_env_when_request_has_no_company(monkeypatch):
    monkeypatch.setenv("APP32_MCP_USER_ID", "3")
    monkeypatch.setenv("APP32_MCP_COMPANY_ID", "9")
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [12, 15],
        },
    )

    context = resolve_mcp_execution_context({})

    assert context.user_id == 3
    assert context.company_id is None
    assert context.metadata["company_resolution_source"] is None


def test_runtime_http_context_never_falls_back_to_process_identity_or_role(monkeypatch):
    monkeypatch.setenv("APP32_MCP_USER_ID", "999")
    monkeypatch.setenv("ACTIVE_USER_ID", "998")
    monkeypatch.setenv("APP32_MCP_FALLBACK_ROLE", "administrador")
    monkeypatch.setenv("APP32_MCP_CHANNEL", "legacy_channel")
    monkeypatch.setenv("APP32_MCP_SURFACE", "admin")
    monkeypatch.setenv("APP32_MCP_CLIENT", "legacy_client")
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda **kwargs: pytest.fail(f"identidade de processo não pode vazar para HTTP: {kwargs}"),
    )
    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-http-no-user",
            user_id=None,
            company_id=9,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "company_id": 9,
            "surface": "user",
            "transport": "streamable_http",
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert context.user_id is None
    assert context.principal_id is None
    assert context.role == "colaborador"
    assert context.permissions == ()
    assert context.channel == "mcp_http"
    assert context.metadata["surface"] == "user"
    assert context.metadata["client"] == "mcp_http"


def test_runtime_normalizes_permission_mapping_into_resource_action_tokens(monkeypatch):
    monkeypatch.delenv("APP32_MCP_USER_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_COMPANY_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_FALLBACK_ROLE", raising=False)

    tokens = set_http_request_context(
        App32McpHttpIdentity(
            token="token-4",
            user_id=4,
            company_id=11,
            fallback_role="colaborador",
            allowed_surfaces=("user",),
        ),
        {
            "user_id": 4,
            "company_id": 11,
            "fallback_role": "colaborador",
            "surface": "user",
        },
    )

    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 77,
            "role": "colaborador",
            "permissions": {"financial": ["view", "create"]},
            "accessible_company_ids": [company_id],
        },
    )

    try:
        context = resolve_mcp_execution_context({})
    finally:
        reset_http_request_context(tokens)

    assert "financial" in context.permissions
    assert "financial.view" in context.permissions
    assert "financial.create" in context.permissions


def test_wrap_mcp_callable_materializes_forward_ref_annotations():
    def sample_tool(note: Optional[str] = None) -> dict[str, str]:
        return {"note": note or ""}

    wrapped = wrap_mcp_callable(sample_tool)
    signature = inspect.signature(wrapped)

    assert signature.parameters["note"].annotation == Optional[str]
    assert signature.return_annotation == dict[str, str]


def test_wrap_mcp_callable_denies_unregistered_capability_before_callback(monkeypatch):
    callback_calls = []
    execution_context = SimpleNamespace(
        user_id=3,
        principal_id=71,
        company_id=9,
        employee_id=23,
        role="colaborador",
        channel="mcp",
        thread_id=None,
        permissions=(),
        accessible_company_ids=(9,),
        metadata={"surface": "user"},
    )

    class _App:
        def app_context(self):
            return nullcontext()

    def unregistered_tool():
        callback_calls.append(True)

    monkeypatch.setattr("app.create_app", lambda: _App())
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload: execution_context)
    monkeypatch.setattr(
        "src.intelligence.tool_catalog.catalog",
        SimpleNamespace(get_tool_capability=lambda tool_name: None),
    )

    with pytest.raises(PermissionError, match="sem capability canônica: unregistered_tool"):
        wrap_mcp_callable(unregistered_tool)()

    assert callback_calls == []


def test_wrap_mcp_callable_never_accepts_human_gate_boolean_from_payload(monkeypatch):
    captured = {}
    execution_context = SimpleNamespace(
        user_id=3,
        principal_id=71,
        company_id=9,
        employee_id=23,
        role="administrador",
        channel="mcp",
        thread_id=None,
        permissions=(),
        accessible_company_ids=(9,),
        metadata={"surface": "admin", "principal_id": 71},
    )

    class _App:
        def app_context(self):
            return nullcontext()

    capability = SimpleNamespace(
        domain="admin",
        risk=SimpleNamespace(value="critical"),
        human_gate=True,
        permissions=(),
        required_context=(),
    )

    def gated_tool(**kwargs):
        return kwargs

    monkeypatch.setattr("app.create_app", lambda: _App())
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload: execution_context)
    monkeypatch.setattr(
        "src.intelligence.tool_catalog.catalog",
        SimpleNamespace(get_tool_capability=lambda tool_name: capability),
    )
    def _evaluate(source, request):
        captured["policy_principal_id"] = source["principal_id"]
        return SimpleNamespace(allowed=False, reason="mutação de alto risco exige confirmação explícita")

    monkeypatch.setattr("src.core.mcp_runtime.evaluate_tool_policy", _evaluate)
    monkeypatch.setattr(
        "services.tool_approval_service.tool_approval_service",
        SimpleNamespace(authorize_and_consume=lambda binding: SimpleNamespace(allowed=True, approval_request_id=91)),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.require_tool_policy",
        lambda source, request: captured.setdefault("confirmed_mutation", request.confirmed_mutation),
    )

    result = wrap_mcp_callable(gated_tool)(
        confirmed_mutation=True,
        human_gate_confirmed=True,
        approval_confirmed=True,
    )

    assert captured["confirmed_mutation"] is True
    assert captured["policy_principal_id"] == 71
    assert result["approval_confirmed"] is True


def test_wrap_mcp_callable_denies_forged_boolean_when_no_persisted_approval(monkeypatch):
    execution_context = SimpleNamespace(
        user_id=3,
        principal_id=71,
        company_id=9,
        employee_id=23,
        role="administrador",
        channel="mcp",
        thread_id=None,
        permissions=(),
        accessible_company_ids=(9,),
        metadata={"surface": "admin", "principal_id": 71},
    )

    class _App:
        def app_context(self):
            return nullcontext()

    capability = SimpleNamespace(
        domain="admin",
        risk=SimpleNamespace(value="critical"),
        human_gate=True,
        permissions=(),
        required_context=(),
    )
    callback_calls = []

    def gated_tool(**kwargs):
        callback_calls.append(kwargs)

    monkeypatch.setattr("app.create_app", lambda: _App())
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload: execution_context)
    monkeypatch.setattr(
        "src.intelligence.tool_catalog.catalog",
        SimpleNamespace(get_tool_capability=lambda tool_name: capability),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.evaluate_tool_policy",
        lambda source, request: SimpleNamespace(allowed=False, reason="mutação de alto risco exige confirmação explícita"),
    )
    monkeypatch.setattr(
        "services.tool_approval_service.tool_approval_service",
        SimpleNamespace(
            authorize_and_consume=lambda binding: SimpleNamespace(
                allowed=False,
                reason="aprovação persistida vigente não encontrada",
            )
        ),
    )
    monkeypatch.setattr(
        "src.core.mcp_runtime.require_tool_policy",
        lambda source, request: pytest.fail("policy final não deve rodar sem aprovação"),
    )

    with pytest.raises(PermissionError, match="aprovação persistida vigente não encontrada"):
        wrap_mcp_callable(gated_tool)(confirmed_mutation=True)

    assert callback_calls == []


def test_runtime_rehydrates_http_request_context_from_current_mcp_request(monkeypatch):
    monkeypatch.setenv("APP32_MCP_HTTP_TOKEN", "token-123")
    monkeypatch.setenv("APP32_MCP_USER_ID", "3")
    monkeypatch.setenv("APP32_MCP_COMPANY_ID", "10")
    monkeypatch.setenv("APP32_MCP_FALLBACK_ROLE", "colaborador")
    auth.load_http_token_registry.cache_clear()

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/",
            "root_path": "",
            "query_string": b"company_id=10",
            "headers": [(b"authorization", b"Bearer token-123")],
            "client": ("127.0.0.1", 12345),
            "server": ("app.gestaoversus.com.br", 443),
        }
    )

    monkeypatch.setattr("src.core.mcp_http_auth._get_current_mcp_server_request", lambda: request)
    monkeypatch.setattr(
        "src.core.mcp_runtime.resolve_runtime_identity",
        lambda user_id, company_id: {
            "company_id": company_id,
            "employee_id": 23,
            "role": "director",
            "permissions": {"approve": True},
            "accessible_company_ids": [company_id],
        },
    )

    context = resolve_mcp_execution_context({})

    assert context.user_id == 3
    assert context.company_id == 10
    assert context.metadata["transport"] == "streamable_http"
    assert context.metadata["client"] == "claude_remote_connector"
