"""A Política de Privacidade precisa ser pública, pois o Google a valida sem login."""

from pathlib import Path

from flask import Flask

from api.routes.public_pages import PUBLIC_PAGE_ENDPOINTS, public_pages_bp

APP_DIR = Path(__file__).resolve().parents[1]


def _client():
    app = Flask(__name__, template_folder=str(APP_DIR / "templates"))
    app.register_blueprint(public_pages_bp)
    return app.test_client()


def test_privacy_policy_is_served_to_anonymous_visitors():
    client = _client()

    for path in ("/privacidade", "/privacy"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.content_type
        body = response.get_data(as_text=True)
        assert "Política de Privacidade" in body
        assert "drive.file" in body
        assert "Uso Limitado" in body


def test_privacy_policy_endpoint_is_exempt_from_login_and_company_selection():
    source = (APP_DIR / "app.py").read_text(encoding="utf-8")

    assert "PUBLIC_PAGE_ENDPOINTS" in source
    assert "public_endpoints.extend(PUBLIC_PAGE_ENDPOINTS)" in source  # sem login
    assert "*PUBLIC_PAGE_ENDPOINTS," in source  # sem empresa selecionada
    assert "public_pages_bp" in source
    assert PUBLIC_PAGE_ENDPOINTS == ("public_pages.privacy_policy",)
