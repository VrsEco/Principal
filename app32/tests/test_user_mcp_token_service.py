from datetime import datetime, timedelta
from types import SimpleNamespace
import base64

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

    assert "Instale a conexão MCP Sapiens Cliente no cliente Claude Code / aba Code do Claude Desktop." in config["activation_prompt"]
    assert "Harness Coordenador do Squad Cliente" in config["activation_prompt"]
    assert "bootstrap_session_context" in config["activation_prompt"]
    assert "describe_app32_available_sapiens_squads_tool" in config["activation_prompt"]
    assert "resolve_app32_sapiens_activation_tool" in config["activation_prompt"]
    assert "resolve_app32_instruction_bundle_tool" in config["activation_prompt"]
    assert "describe_app32_squad_runtime_tool" in config["activation_prompt"]
    assert "Autenticação: Bearer Token" in config["activation_prompt"]
    assert "describe_app32_squad_runtime_tool" in config["activation_prompt"]
    assert '"transport": "http"' in config["technical_config_text"]
    assert '"Authorization": "Bearer mcpu_token_real"' in config["technical_config_text"]
    assert '"experience_label": "Sapiens Cliente"' in config["technical_config_text"]
    assert config["guided_connection_fields"][0]["label"] == "Nome da conexão"
    assert any(field["label"] == "Registry MCP do Claude Code" for field in config["guided_connection_fields"])
    assert config["guided_install_steps"][0].startswith("No terminal do Windows, confirme que o Claude Code")
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
    assert config["runtime_label"] == "Claude Code / aba Code do Claude Desktop"
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
    assert "claude mcp add --scope user --transport http sapiens-user" in config["cli_install_text"]
    assert config["powershell_install_command"].startswith("powershell -ExecutionPolicy Bypass -EncodedCommand ")
    decoded = base64.b64decode(config["install_command"].split(" -EncodedCommand ", 1)[1]).decode("utf-16le")
    assert "install-sapiens-runtime.ps1" in decoded
    assert "-ClientRuntime 'claude'" in decoded
    assert "-ServerUrl 'https://app.gestaoversus.com.br/mcp/user/'" in decoded
    assert "-BearerToken 'mcpu_token_real'" in decoded
    assert "comando único do APP32" in config["instruction_text"]
    assert "claude mcp add" in config["instruction_text"]
    assert "Claude Code, Codex ou Antigravity" in config["instruction_text"]
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
