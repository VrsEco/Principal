from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_oauth_recovery_is_self_service_audited_and_never_accepts_tenant_from_browser():
    service = (ROOT / "services" / "oauth_connection_recovery_service.py").read_text(encoding="utf-8")
    route = (ROOT / "api" / "routes" / "auth.py").read_text(encoding="utf-8")
    model = (ROOT / "models" / "identity_provisioning_outbox.py").read_text(encoding="utf-8")

    assert "OAuthConnectionRecoveryAudit" in model
    assert "recover_authenticated_user(self, *, user_id: int)" in service
    assert "send_password_setup_email=True" in service
    assert "suspend_stale_grants=True" in service
    assert 'status.in_(["processing", "succeeded"])' in service
    signature = service.split("def recover_authenticated_user", 1)[1].split(") -> dict:", 1)[0]
    assert "company_id" not in signature
    assert "same_origin_verified()" in route
    assert "current_user.id" in route


def test_keycloak_email_theme_keeps_native_action_link_and_versus_identity():
    theme_root = ROOT / "deploy" / "keycloak" / "configr" / "themes" / "versus" / "email"
    template = (theme_root / "html" / "executeActions.ftl").read_text(encoding="utf-8")
    text_template = (theme_root / "text" / "executeActions.ftl").read_text(encoding="utf-8")
    properties = (theme_root / "theme.properties").read_text(encoding="utf-8")

    assert "parent=keycloak" in properties
    assert "${link}" in template
    assert "?html" not in template
    assert "${link}" in text_template
    assert "linkExpirationFormatter(linkExpiration)" in template
    assert "Versus Gestão Corporativa" in template

