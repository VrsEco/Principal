from pathlib import Path


def test_user_administration_exposes_mcp_oauth_lifecycle_without_tenant_fallback():
    root = Path(__file__).resolve().parents[1]
    routes = (root / "api" / "routes" / "users.py").read_text(encoding="utf-8")
    service = (root / "services" / "mcp_oauth_onboarding_service.py").read_text(encoding="utf-8")
    template = (root / "templates" / "usuarios" / "editar.html").read_text(encoding="utf-8")

    assert "/mcp-oauth/enable" in routes
    assert "/mcp-oauth/revoke" in routes
    assert "Employee.query.filter_by(user_id=user_id, company_id=company_id, status=\"active\")" in service
    assert "PrincipalCompanyGrant" in service
    assert "content-mcp-oauth" in template
    assert "Revogar apenas o acesso MCP OAuth" in template
