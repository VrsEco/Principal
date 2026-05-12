from datetime import datetime, timedelta
from types import SimpleNamespace

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

    assert config["url"] == "https://app.gestaoversus.com.br/mcp/user/?company_id=12"



def test_build_client_config_exposes_activation_prompt_and_technical_output(monkeypatch):
    service = token_service_module.user_mcp_token_service
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_ensure_app_context", staticmethod(lambda: __import__("contextlib").nullcontext()))
    monkeypatch.setattr(token_service_module, "User", SimpleNamespace(query=SimpleNamespace(get=lambda _id: SimpleNamespace(id=7, is_active=True))))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_normalize_surface", staticmethod(lambda surface: "user"))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "_resolve_explicit_company_id_for_user", staticmethod(lambda user, company_id: 9))
    monkeypatch.setattr(token_service_module.UserMcpTokenService, "list_accessible_companies", staticmethod(lambda user: [{"id": 9, "label": "AA - Versus Gestao Corporativa"}]))
    monkeypatch.setenv("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")

    config = service.build_client_config(user_id=7, plaintext_token="mcpu_token_real", company_id=9)

    assert "ative o Sapiens" in config["activation_prompt"]
    assert "◆ SAPIENS · Gestão Versus ● ativo" in config["activation_prompt"]
    assert "Este cliente não suporta ativação automática do Sapiens." in config["activation_prompt"]
    assert '"token": "mcpu_token_real"' in config["technical_config_text"]


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
    assert config["resolved_profile"] == "squad_cliente"
    assert config["resolved_surface"] == "user"
    assert config["install_mode"] == "self_service"
    assert "install-claude-laboratorio.ps1" in config["install_command"]


def test_build_client_config_marks_admin_surface_as_controlled(monkeypatch):
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
        runtime="antigravity",
        squad="squad_versus",
    )

    assert config["resolved_profile"] == "squad_versus"
    assert config["resolved_surface"] == "admin"
    assert config["install_mode"] == "controlled"
    assert config["supports_personal_token"] is False


def test_resolve_for_http_request_returns_none_for_unsupported_surface():
    service = token_service_module.user_mcp_token_service

    resolved = service.resolve_for_http_request(
        token="mcpu_fake",
        surface="admin",
        company_id=10,
        client_name="laboratorio",
    )

    assert resolved is None
