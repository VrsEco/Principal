from __future__ import annotations

from datetime import datetime, timezone

from src.intelligence.security import mcp_mutation_guard as guard
def test_evaluate_mutation_limit_blocks_when_threshold_reached(monkeypatch):
    monkeypatch.setattr(
        guard,
        "load_mutation_limit_policy",
        lambda: guard.MutationLimitPolicy(
            profile_name="default",
            create_limit=2,
            update_limit=3,
            delete_limit=1,
            restore_limit=1,
            window_hours=24,
        ),
    )
    monkeypatch.setattr(guard, "count_recent_mutations", lambda **kwargs: 2)
    monkeypatch.setattr(
        guard,
        "resolve_mutation_limit_policy",
        lambda **kwargs: guard.MutationLimitPolicy(
            profile_name="default",
            create_limit=2,
            update_limit=3,
            delete_limit=1,
            restore_limit=1,
            window_hours=24,
        ),
    )
    monkeypatch.setattr(
        guard,
        "get_mutation_window_reset_at",
        lambda **kwargs: datetime(2026, 5, 17, 18, 0, tzinfo=timezone.utc),
    )

    decision = guard.evaluate_mutation_limit(
        action="create",
        company_id=9,
        user_id=7,
    )

    assert decision.allowed is False
    assert decision.limit == 2
    assert "atingido" in decision.reason
    assert decision.reset_at == "2026-05-17T18:00:00+00:00"


def test_evaluate_mutation_limit_requires_user_and_company(monkeypatch):
    guard_policy = guard.MutationLimitPolicy(
        profile_name="default",
        create_limit=20,
        update_limit=50,
        delete_limit=10,
        restore_limit=10,
        window_hours=24,
    )
    monkeypatch.setattr(guard, "resolve_mutation_limit_policy", lambda **kwargs: guard_policy)
    decision = guard.evaluate_mutation_limit(action="update", company_id=None, user_id=7)

    assert decision.allowed is False
    assert "usuário associado" in decision.reason


def test_resolve_mutation_limit_policy_supports_binding_by_company_connector_and_scenario(monkeypatch):
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_PROFILES_JSON",
        '{"implantacao":{"create_limit":500,"update_limit":200,"delete_limit":20,"restore_limit":20,"window_hours":24}}',
    )
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_BINDINGS_JSON",
        '[{"profile":"implantacao","company_id":10,"connector":"teste_real","scenario":"implantacao"}]',
    )
    monkeypatch.setenv("APP32_MCP_CONNECTOR", "teste_real")
    monkeypatch.setenv("APP32_MCP_MUTATION_SCENARIO", "implantacao")

    policy = guard.resolve_mutation_limit_policy(company_id=10, user_id=7)

    assert policy.profile_name == "implantacao"
    assert policy.create_limit == 500
    assert policy.is_override is True
    assert "company_id=10" in str(policy.binding_scope)


def test_record_mutation_success_embeds_mutation_policy_metadata(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        guard,
        "resolve_mutation_limit_policy",
        lambda **kwargs: guard.MutationLimitPolicy(
            profile_name="implantacao",
            create_limit=500,
            update_limit=200,
            delete_limit=20,
            restore_limit=20,
            window_hours=24,
            override_reason="Teste Real",
            binding_scope="company_id=10, connector=teste_real",
            is_override=True,
        ),
    )
    monkeypatch.setattr(guard, "emit_ai_execution_audit_event", lambda record: captured.setdefault("record", record.model_dump(mode="python")) or {"ok": True})

    guard.record_mutation_success(
        action="create",
        company_id=10,
        user_id=7,
        tool_name="create_project",
        domain="projects",
        metadata={"project_code": "M1.J.10"},
    )

    metadata = captured["record"]["metadata"]
    assert metadata["project_code"] == "M1.J.10"
    assert metadata["mutation_limit_policy"]["profile_name"] == "implantacao"
    assert metadata["mutation_limit_policy"]["is_override"] is True


def test_resolve_mutation_limit_policy_uses_http_request_context_binding_after_restart(monkeypatch):
    monkeypatch.delenv("APP32_MCP_CONNECTOR", raising=False)
    monkeypatch.delenv("APP32_MCP_MUTATION_SCENARIO", raising=False)
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_PROFILES_JSON",
        '{"implantacao":{"create_limit":500,"update_limit":200,"delete_limit":20,"restore_limit":20,"window_hours":24}}',
    )
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_BINDINGS_JSON",
        (
            '[{"profile":"implantacao","user_id":3,"company_id":10,'
            '"connector":"claude_remote_connector"}]'
        ),
    )
    monkeypatch.setattr(
        guard,
        "_get_runtime_request_metadata",
        lambda: {
            "http": {
                "user_id": 3,
                "company_id": 10,
                "client": "claude_remote_connector",
                "runtime_profile": "implantacao",
                "fallback_role": "colaborador",
            },
            "sapiens": {"user_id": 3, "company_id": 10, "channel": "claude_code", "metadata": {}},
        },
    )

    policy = guard.resolve_mutation_limit_policy(company_id=10, user_id=3)

    assert policy.profile_name == "implantacao"
    assert policy.create_limit == 500
    assert policy.is_override is True
    assert "user_id=3" in str(policy.binding_scope)
    assert "company_id=10" in str(policy.binding_scope)
    assert "connector=claude_remote_connector" in str(policy.binding_scope)


def test_resolve_mutation_limit_policy_uses_sapiens_context_metadata_when_http_context_absent(monkeypatch):
    monkeypatch.delenv("APP32_MCP_CONNECTOR", raising=False)
    monkeypatch.delenv("APP32_MCP_MUTATION_SCENARIO", raising=False)
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_PROFILES_JSON",
        '{"implantacao":{"create_limit":500,"update_limit":200,"delete_limit":20,"restore_limit":20,"window_hours":24}}',
    )
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_BINDINGS_JSON",
        '[{"profile":"implantacao","company_id":10,"connector":"claude_remote_connector","scenario":"implantacao"}]',
    )
    monkeypatch.setattr(
        guard,
        "_get_runtime_request_metadata",
        lambda: {
            "http": {},
            "sapiens": {
                "user_id": 3,
                "company_id": 10,
                "channel": "claude_code",
                "metadata": {
                    "client": "claude_remote_connector",
                    "runtime_profile": "implantacao",
                },
            },
        },
    )

    policy = guard.resolve_mutation_limit_policy(company_id=10, user_id=3)

    assert policy.profile_name == "implantacao"
    assert policy.create_limit == 500
    assert policy.is_override is True


def test_resolve_mutation_limit_policy_uses_app32_mcp_client_env_as_connector_fallback(monkeypatch):
    monkeypatch.delenv("APP32_MCP_CONNECTOR", raising=False)
    monkeypatch.setenv("APP32_MCP_CLIENT", "claude_remote_connector")
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_PROFILES_JSON",
        '{"implantacao":{"create_limit":500,"update_limit":200,"delete_limit":20,"restore_limit":20,"window_hours":24}}',
    )
    monkeypatch.setenv(
        "APP32_MCP_MUTATION_LIMIT_BINDINGS_JSON",
        '[{"profile":"implantacao","company_id":10,"connector":"claude_remote_connector"}]',
    )
    monkeypatch.setattr(
        guard,
        "_get_runtime_request_metadata",
        lambda: {"http": {}, "sapiens": {"user_id": None, "company_id": None, "channel": None, "metadata": {}}},
    )

    policy = guard.resolve_mutation_limit_policy(company_id=10, user_id=3)

    assert policy.profile_name == "implantacao"
    assert policy.create_limit == 500
    assert policy.is_override is True

