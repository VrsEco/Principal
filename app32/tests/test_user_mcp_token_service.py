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
