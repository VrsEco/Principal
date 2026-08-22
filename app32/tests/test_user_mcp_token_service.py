from datetime import date, datetime, timedelta
from types import SimpleNamespace
import base64
import contextlib
import os
import sys

import services.user_mcp_token_service as token_service_module


def test_build_notification_body_for_d3_contains_renewal_instruction():
    now = datetime.utcnow()
    record = SimpleNamespace(
        status="active",
        expires_at=now + timedelta(days=3),
        user_id=7,
    )
    user = SimpleNamespace(
        id=7,
        name="Ana",
        email="ana@empresa.com",
        whatsapp="5571999999999",
        is_active=True,
    )

    subject, html_body, whatsapp_message = token_service_module.user_mcp_token_service._build_notification_body(
        user,
        record,
        days_remaining=3,
    )

    assert "3 dias" in subject
    assert "/profile" in html_body
    assert "renove o token" in whatsapp_message.lower()


def test_issue_token_revokes_only_same_runtime_connector(monkeypatch):
    service = token_service_module.user_mcp_token_service
    fake_user = SimpleNamespace(id=7)
    now = datetime(2026, 7, 9, 12, 0, 0)

    existing_claude = SimpleNamespace(
        user_id=7,
        status="active",
        last_client_name="claude:squad_cliente",
        revoked_at=None,
        updated_at=None,
    )
    existing_codex = SimpleNamespace(
        user_id=7,
        status="active",
        last_client_name="codex:squad_cliente",
        revoked_at=None,
        updated_at=None,
    )
    created_records = []

    class FakeQuery:
        def filter_by(self, **kwargs):
            assert kwargs == {"user_id": 7, "status": "active"}
            return self

        def all(self):
            return [existing_claude, existing_codex]

    class FakeUserMcpToken:
        query = FakeQuery()

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            created_records.append(self)

    class FakeSession:
        def add(self, record):
            created_records.append(record)

        def commit(self):
            pass

    class FakeUserQuery:
        def filter_by(self, **kwargs):
            assert kwargs == {"id": 7}
            return self

        def with_for_update(self):
            return self

        def first(self):
            return fake_user

    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=FakeUserQuery()))
    monkeypatch.setattr(token_service_module, "UserMcpToken", FakeUserMcpToken)
    monkeypatch.setattr(token_service_module.db, "session", FakeSession())
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_utcnow", staticmethod(lambda: now))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_generate_plaintext_token", staticmethod(lambda: "mcpu_new"))

    record, plaintext = service._issue_token(
        fake_user,
        created_by_user_id=7,
        runtime="claude",
        squad="squad_cliente",
    )

    assert plaintext == "mcpu_new"
    assert record.last_client_name == "claude:squad_cliente"
    assert existing_claude.status == "revoked"
    assert existing_claude.revoked_at == now
    assert existing_codex.status == "active"
    assert existing_codex.revoked_at is None


def test_ensure_app_context_disables_bootstrap_when_creating_mcp_token_app(monkeypatch):
    service = token_service_module.user_mcp_token_service
    captured = {}

    class FakeApp:
        def app_context(self):
            return contextlib.nullcontext()

    def fake_create_app(config_name):
        captured["config_name"] = config_name
        captured["APP_BOOTSTRAP_DB_SCHEMA"] = os.environ.get("APP_BOOTSTRAP_DB_SCHEMA")
        captured["APP_BOOTSTRAP_RUNTIME_SERVICES"] = os.environ.get("APP_BOOTSTRAP_RUNTIME_SERVICES")
        return FakeApp()

    monkeypatch.delenv("APP_BOOTSTRAP_DB_SCHEMA", raising=False)
    monkeypatch.delenv("APP_BOOTSTRAP_RUNTIME_SERVICES", raising=False)
    monkeypatch.setattr(token_service_module, "has_app_context", lambda: False)
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(create_app=fake_create_app))

    with service._ensure_app_context():
        pass

    assert captured == {
        "config_name": "production",
        "APP_BOOTSTRAP_DB_SCHEMA": "0",
        "APP_BOOTSTRAP_RUNTIME_SERVICES": "0",
    }
    assert os.environ.get("APP_BOOTSTRAP_DB_SCHEMA") is None
    assert os.environ.get("APP_BOOTSTRAP_RUNTIME_SERVICES") is None


def test_build_client_config_uses_trailing_slash(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 12))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 12, "label": "Empresa 12"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(user_id=7, plaintext_token="abc", company_id=12)

    assert config["url"] == "https://app.gestaoversus.com.br/mcp/user/"



def test_build_client_config_exposes_activation_prompt_and_technical_output(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 9))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 9, "label": "AA - Versus Gestao Corporativa"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(user_id=7, plaintext_token="mcpu_token_real", company_id=9)

    assert "Instale a conexão MCP Sapiens Cliente no cliente Claude Windows Desktop / Claude CLI." in config["activation_prompt"]
    assert "Harness Coordenador do Squad Cliente" in config["activation_prompt"]
    assert "Identidade MCP confirmada:" in config["activation_prompt"]
    assert "- user_id: 7" in config["activation_prompt"]
    assert "- empresa ativa: AA - Versus Gestao Corporativa" in config["activation_prompt"]
    assert "bootstrap_session_context" in config["activation_prompt"]
    assert "describe_app32_available_sapiens_squads_tool" in config["activation_prompt"]
    assert "resolve_app32_sapiens_activation_tool" in config["activation_prompt"]
    assert "resolve_app32_instruction_bundle_tool" in config["activation_prompt"]
    assert "describe_app32_squad_runtime_tool" in config["activation_prompt"]
    assert "Sapiens (Versus) disponível. Como posso te ajudar?" in config["activation_prompt"]
    assert config["activation_welcome_opening"].startswith("Sapiens (Versus) disponível.")
    assert "Autenticação: Bearer Token" in config["activation_prompt"]
    assert "describe_app32_squad_runtime_tool" in config["activation_prompt"]
    assert '"transport": "http"' in config["technical_config_text"]
    assert '"Authorization": "Bearer mcpu_token_real"' in config["technical_config_text"]
    assert '"experience_label": "Sapiens Cliente"' in config["technical_config_text"]
    assert config["guided_connection_fields"][0]["label"] == "Nome da conexão"
    assert any(field["label"] == "Usuário Normal" for field in config["guided_connection_fields"])
    assert any(field["label"] == "Usuário Avançado" for field in config["guided_connection_fields"])
    assert any(field["label"] == "Registry MCP do Claude Code" for field in config["guided_connection_fields"])
    assert config["guided_install_steps"][0].startswith("Usuário Normal")
    assert config["identity"]["user_id"] == 7
    assert config["identity"]["active_company_id"] == 9
    assert config["identity"]["accessible_company_ids"] == [9]
    assert "AA - Versus Gestao Corporativa" in config["identity_summary_text"]
    assert config["validation_prompt"] == (
        "Digite Sapiens On (ou /sapiens-on) e confirme o fluxo com "
        "bootstrap_session_context, describe_app32_available_sapiens_squads_tool e "
        "resolve_app32_sapiens_activation_tool."
    )
    assert "Harness inicial: Harness Coordenador do Squad Cliente" in config["harness_summary_text"]
    assert "Pré-flight obrigatório:" in config["smoke_guided_text"]
    assert "bootstrap_session_context" in config["smoke_guided_text"]
    assert "resolve_app32_instruction_bundle_tool" in config["smoke_guided_text"]
    assert "Onboarding operacional desta instalação:" in config["onboarding_summary_text"]
    assert "Badge esperado da sessão: Sapiens Cliente On" in config["onboarding_summary_text"]
    assert config["session_badge"] == "Sapiens Cliente On"
    assert config["preflight_tools"] == [
        "bootstrap_session_context",
        "describe_app32_session_company_scope_tool",
        "describe_app32_available_sapiens_squads_tool",
    ]
    assert config["activation_tool"] == "resolve_app32_sapiens_activation_tool"
    assert config["startup_tools"][0] == "bootstrap_session_context"
    assert any(item["command"] == "/sapiens-cliente-on" for item in config["activation_commands"])
    assert any(item["command"] == "/sapiens-on" for item in config["activation_commands"])
    assert any(item["command"] == "Sapiens Off" for item in config["deactivation_commands"])
    assert "powershell -ExecutionPolicy Bypass -EncodedCommand" in config["activation_commands_install_command"]
    encoded = config["activation_commands_install_command"].split(" -EncodedCommand ", 1)[1]
    decoded = base64.b64decode(encoded).decode("utf-16le")
    assert "raw.githubusercontent.com/VrsEco/Principal/main/app32/scripts/installers/install-claude-sapiens-slash-commands.ps1" in decoded
    assert "Invoke-WebRequest" in decoded


def test_build_client_config_resolves_claude_squad_cliente_installer(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 10))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 10, "label": "M1 - Empresa Laboratorio"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        plaintext_token="mcpu_token_real",
        company_id=10,
        runtime="claude",
        squad="squad_cliente",
    )

    assert config["runtime"] == "claude"
    assert config["runtime_label"] == "Claude Windows Desktop / Claude CLI"
    assert config["resolved_profile"] == "squad_cliente"
    assert config["resolved_surface"] == "user"
    assert config["install_mode"] == "self_service"
    assert config["availability_label"] == "Instalação automática"
    assert config["actor_type"] == "client_agent"
    assert config["experience_label"] == "Sapiens Cliente"
    assert config["command_alias"] == "/sapiens-cliente-on"
    assert config["harness_key"] == "harness_coordenador_cliente_v1"
    assert config["harness_label"] == "Harness Coordenador do Squad Cliente"
    assert config["install_command"].startswith("powershell -ExecutionPolicy Bypass -EncodedCommand ")
    assert config["copy_install_command_text"].startswith("powershell -ExecutionPolicy Bypass -EncodedCommand ")
    assert "Usuário Avançado — Claude CLI via PowerShell" in config["cli_install_text"]
    assert "claude mcp add --scope user --transport http sapiens-user" in config["cli_install_text"]
    assert config["powershell_install_command"].startswith("powershell -ExecutionPolicy Bypass -EncodedCommand ")
    decoded = base64.b64decode(config["install_command"].split(" -EncodedCommand ", 1)[1]).decode("utf-16le")
    assert "install-sapiens-claude-desktop-windows.ps1" in decoded
    assert "-ServerName 'Sapiens Cliente'" in decoded
    assert "-ServerUrl 'https://app.gestaoversus.com.br/mcp/user/'" in decoded
    assert "-BearerToken 'mcpu_token_real'" in decoded
    assert config["normal_install_command"] == config["install_command"]
    assert "proxy stdio" in config["normal_install_text"]
    assert config["install_profiles"]["normal"]["label"] == "Usuário Normal - Claude Windows Desktop"
    assert config["advanced_install_command"].startswith("powershell -ExecutionPolicy Bypass -EncodedCommand ")
    advanced_decoded = base64.b64decode(config["advanced_install_command"].split(" -EncodedCommand ", 1)[1]).decode("utf-16le")
    assert "install-sapiens-runtime.ps1" in advanced_decoded
    assert "-ClientRuntime 'claude'" in advanced_decoded
    assert "Usuário Normal" in config["instruction_text"]


def test_build_client_config_marks_placeholder_as_not_executable(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 10))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 10, "label": "M1 - Empresa Laboratorio"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        company_id=10,
        runtime="claude",
        squad="squad_cliente",
    )

    assert config["has_plaintext_token"] is False
    assert config["token_required"] is True
    assert config["token_placeholder"] == "TOKEN_GERADO_APENAS_NA_RENOVACAO"
    decoded = base64.b64decode(config["normal_install_command"].split(" -EncodedCommand ", 1)[1]).decode("utf-16le")
    assert "TOKEN_GERADO_APENAS_NA_RENOVACAO" in decoded
    assert "Usuário Avançado" in config["instruction_text"]
    assert "Claude CLI/registry HTTP" in config["instruction_text"]
    assert "proxy stdio" in config["instruction_text"]
    assert "/sapiens-cliente-on" in config["activation_prompt"]
    assert "/sapiens-on" in config["activation_prompt"]
    assert "Use a conexão MCP Sapiens Cliente desta sessão." in config["activation_prompt"]
    assert "Quando o usuário digitar `Sapiens On`, `sapiens on` ou `/sapiens-on`" in config["activation_prompt"]
    assert "Com qual squad você vai trabalhar?" in config["activation_prompt"]
    assert "Sapiens Off" in config["activation_prompt"]


def test_build_client_config_marks_admin_surface_as_controlled(monkeypatch):
    service = token_service_module.user_mcp_token_service
    fake_user = SimpleNamespace(id=7, is_active=True, role="admin")
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: fake_user)))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 10))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 10, "label": "M1 - Empresa Laboratorio"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        plaintext_token="mcpu_token_real",
        company_id=10,
        runtime="antigravity",
        squad="squad_versus",
    )

    assert config["resolved_profile"] == "squad_versus"
    assert config["resolved_surface"] == "admin"
    assert config["url"] == "https://app.gestaoversus.com.br/mcp/admin/?company_id=10"
    assert config["experience_label"] == "Sapiens Consultor"
    assert config["install_mode"] == "self_service"
    assert config["supports_personal_token"] is False
    assert config["runtime_locked"] is False
    assert config["runtime_blocked"] is False


def test_build_status_payload_exposes_identity_and_scope(monkeypatch):
    service = token_service_module.user_mcp_token_service
    fake_user = SimpleNamespace(
        id=7,
        is_active=True,
        email="ana@empresa.com",
        name="Ana",
        role="admin",
    )
    fake_record = SimpleNamespace(
        status="active",
        token_prefix="mcpu_prefix",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
        last_used_at=None,
        last_client_name="Claude",
        last_surface="user",
        last_company_id=12,
    )
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "list_accessible_companies",
        staticmethod(lambda user: [{"id": 10, "label": "Empresa 10"}, {"id": 12, "label": "Empresa 12"}]),
    )
    monkeypatch.setattr(token_service_module, "get_default_company_id", lambda user=None: 10)
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "_utcnow",
        staticmethod(lambda: datetime(2026, 5, 18)),
    )

    payload = service._build_status_payload(fake_user, fake_record)

    assert payload["identity"]["user_id"] == 7
    assert payload["identity"]["email"] == "ana@empresa.com"
    assert payload["identity"]["active_company_id"] == 12
    assert payload["identity"]["accessible_company_ids"] == [10, 12]
    assert payload["identity"]["accessible_companies_count"] == 2
    assert "Identidade MCP confirmada:" in payload["identity_summary_text"]
    assert "- user_id: 7" in payload["identity_summary_text"]
    assert "- empresa ativa: Empresa 12" in payload["identity_summary_text"]


def test_resolve_for_http_request_returns_none_for_unsupported_surface():
    service = token_service_module.user_mcp_token_service

    resolved = service.resolve_for_http_request(
        token="mcpu_fake",
        surface="admin",
        company_id=10,
        client_name="laboratorio",
    )

    assert resolved is None


def test_build_client_config_marks_user_surface_as_dynamic_scope_when_no_explicit_company(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: None))
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "list_accessible_companies",
        staticmethod(lambda user: [{"id": 10, "label": "Empresa 10"}, {"id": 12, "label": "Empresa 12"}]),
    )
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(user_id=7, plaintext_token="abc", company_id=None)

    assert config["url"] == "https://app.gestaoversus.com.br/mcp/user/"
    assert config["company_label"] == "Escopo dinâmico multiempresa"
    assert config["company_context_rules"]["multiple_companies"] is True


def test_build_runtime_company_scope_requires_explicit_selection_for_multi_company(monkeypatch):
    service = token_service_module.user_mcp_token_service
    user = SimpleNamespace(id=7, is_active=True)
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "list_accessible_companies",
        staticmethod(lambda current_user: [{"id": 10, "label": "Empresa 10"}, {"id": 12, "label": "Empresa 12"}]),
    )
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "_resolve_explicit_company_id_for_user",
        staticmethod(lambda current_user, company_id: int(company_id) if company_id in {10, 12} else None),
    )

    scope = service.build_runtime_company_scope(user, requested_company_id=None, persisted_company_id=None)

    assert scope["active_company_id"] is None
    assert scope["selection_required_for_mutations"] is True
    assert scope["accessible_company_ids"] == [10, 12]


def test_build_runtime_company_scope_marks_selected_company_from_persisted_context(monkeypatch):
    service = token_service_module.user_mcp_token_service
    user = SimpleNamespace(id=7, is_active=True)
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "list_accessible_companies",
        staticmethod(
            lambda current_user: [
                {"id": 1, "label": "Save Water", "selected": True},
                {"id": 6, "label": "Ventana", "selected": False},
            ]
        ),
    )
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "_resolve_explicit_company_id_for_user",
        staticmethod(lambda current_user, company_id: int(company_id) if company_id in {1, 6} else None),
    )

    scope = service.build_runtime_company_scope(user, persisted_company_id=6)

    assert scope["active_company_id"] == 6
    assert scope["active_company_label"] == "Ventana"
    assert [item["selected"] for item in scope["companies"]] == [False, True]


def test_build_client_config_exposes_squad_cliente_harness_catalog(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 10))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 10, "label": "M1 - Empresa Laboratorio"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        plaintext_token="mcpu_token_real",
        company_id=10,
        runtime="claude",
        squad="squad_cliente",
    )

    assert [item["key"] for item in config["available_harnesses"]] == [
        "harness_coordenador_cliente_v1",
        "harness_comercial_cliente_v1",
        "harness_operacional_cliente_v1",
        "harness_admfin_cliente_v1",
    ]
    assert [item["key"] for item in config["official_agents"]] == ["SC-COORD", "SC-COM", "SC-OPS", "SC-ADM"]
    assert config["official_phase_label"] == "Fase 1 oficial"
    assert "Harness inicial: Harness Coordenador do Squad Cliente" in config["activation_prompt"]


def test_build_client_config_restricts_advanced_squad_for_client_role(monkeypatch):
    service = token_service_module.user_mcp_token_service
    fake_user = SimpleNamespace(id=7, is_active=True, role="client")
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: fake_user)))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 10))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 10, "label": "M1 - Empresa Laboratorio"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        plaintext_token="mcpu_token_real",
        company_id=10,
        runtime="antigravity",
        squad="squad_versus",
    )

    assert config["squad"] == "squad_cliente"
    assert config["experience_label"] == "Sapiens Cliente"
    assert config["resolved_surface"] == "user"
    assert config["allowed_squads"] == ["squad_cliente"]
    assert config["runtime_blocked"] is True
    assert config["availability_label"] == "Indisponível para seu perfil"
    assert config["install_command"] is None
    assert config["supports_personal_token"] is False


def test_build_client_config_keeps_other_runtime_guided_for_squad_cliente(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 10))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 10, "label": "M1 - Empresa Laboratorio"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        plaintext_token="mcpu_token_real",
        company_id=10,
        runtime="other",
        squad="squad_cliente",
    )

    assert config["availability_label"] == "Instalação guiada"
    assert config["install_mode"] == "guided"
    assert "Durante a instalação, use o token MCP pessoal gerado nesta página." in config["instruction_text"]


def test_build_client_config_requires_company_for_antigravity_privileged_surface(monkeypatch):
    service = token_service_module.user_mcp_token_service
    fake_user = SimpleNamespace(id=7, is_active=True, role="consultant")
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: fake_user)))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: None))
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "_resolve_runtime_company_context",
        staticmethod(lambda user, requested_company_id=None, persisted_company_id=None: (None, None, (10, 12))),
    )
    monkeypatch.setattr(
        token_service_module.UserMcpTokenService,
        "list_accessible_companies",
        staticmethod(lambda user: [{"id": 10, "label": "Empresa 10"}, {"id": 12, "label": "Empresa 12"}]),
    )
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(
        user_id=7,
        plaintext_token="mcpu_token_real",
        company_id=None,
        runtime="antigravity",
        squad="squad_versus",
    )

    assert config["resolved_surface"] == "admin"
    assert config["requires_company_selection"] is True
    assert config["install_mode"] == "selection_required"
    assert config["install_command"] is None
    assert "company_id explícito" in config["instruction_text"]


def test_expiration_notification_skips_token_locked_by_another_worker(monkeypatch):
    service = token_service_module.user_mcp_token_service
    candidate = SimpleNamespace(id=91, status="active", expires_at=datetime(2026, 7, 16), notice_d3_sent_at=None, notice_d0_sent_at=None, user_id=7)
    calls = []

    class FakeTokenQuery:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return [candidate]

        def filter_by(self, **kwargs):
            assert kwargs == {"id": 91}
            return self

        def with_for_update(self, **kwargs):
            calls.append(kwargs)
            return self

        def populate_existing(self):
            return self

        def first(self):
            return None

    fake_columns = SimpleNamespace(expires_at=SimpleNamespace(asc=lambda: "expires_at"))
    monkeypatch.setattr(token_service_module, "UserMcpToken", SimpleNamespace(query=FakeTokenQuery(), status="status", **fake_columns.__dict__))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: contextlib.nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: (_ for _ in ()).throw(AssertionError("não deve enviar")))))
    monkeypatch.setattr(token_service_module.db, "session", SimpleNamespace(commit=lambda: None))

    result = service.send_expiration_notifications(reference_date=date(2026, 7, 13))

    assert result == {"processed": 0, "notified": 0}
    assert calls == [{"skip_locked": True}]
