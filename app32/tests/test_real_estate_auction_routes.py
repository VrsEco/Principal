import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import real_estate_auctions as route
from services.rbac_permission_catalog_service import RbacPermissionCatalogService


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    app.register_blueprint(route.real_estate_auctions_bp)
    return app


def _company():
    return SimpleNamespace(id=31, name="GanduInvest", client_code="GND")


def test_workspace_route_uses_service_and_tenant_filters(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(route, "_resolve_company", lambda **kwargs: _company())
    monkeypatch.setattr(route, "_has_module_permission", lambda company_id, action: True)
    monkeypatch.setattr(
        route.RealEstateAuctionService,
        "get_workspace",
        lambda company_id, include_disabled=True: {
            "settings": {"module_enabled": True, "display_name": "Leilões Imobiliários"},
            "summary": {"properties_total": 1, "status_counts": {}, "triage_counts": {}},
            "sources": [],
            "recent_properties": [],
        },
    )

    def fake_list(company_id, **kwargs):
        captured["list"] = {"company_id": company_id, **kwargs}
        return [{"id": 7, "code": "GND-001", "address": "Rua A", "status": "in_analysis", "triage_status": "pending"}]

    monkeypatch.setattr(route.RealEstateAuctionService, "list_properties", fake_list)
    monkeypatch.setattr(
        route,
        "render_template",
        lambda template_name, **context: captured.update({"template": template_name, "context": context}) or "ok",
    )

    response = app.test_client().get("/real-estate-auctions?company_id=31&status=in_analysis&city=Feira")

    assert response.status_code == 200
    assert captured["template"] == "modules/real_estate_auctions/workspace.html"
    assert captured["context"]["company_id"] == 31
    assert captured["context"]["properties"][0]["code"] == "GND-001"
    assert captured["context"]["can_manage_sources"] is True
    assert captured["list"]["company_id"] == 31
    assert captured["list"]["status"] == "in_analysis"
    assert captured["list"]["city"] == "Feira"


def test_create_property_api_is_thin_and_tenant_scoped(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(route, "_resolve_company", lambda **kwargs: _company())

    def fake_create(company_id, payload, *, user_id=None):
        captured["create"] = {"company_id": company_id, "payload": payload, "user_id": user_id}
        return {"id": 10, "company_id": company_id, "code": payload["code"], "address": payload["address"]}

    monkeypatch.setattr(route.RealEstateAuctionService, "create_property", fake_create)

    response = app.test_client().post(
        "/api/real-estate-auctions/properties?company_id=31",
        json={"code": "GND-010", "address": "Av. Brasil"},
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["property"]["company_id"] == 31
    assert captured["create"]["company_id"] == 31
    assert captured["create"]["payload"] == {"code": "GND-010", "address": "Av. Brasil"}


def test_list_properties_api_wraps_domain_error(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(route, "_resolve_company", lambda **kwargs: _company())

    def fake_list(*args, **kwargs):
        raise route.RealEstateAuctionError("Módulo não habilitado.")

    monkeypatch.setattr(route.RealEstateAuctionService, "list_properties", fake_list)

    response = app.test_client().get("/api/real-estate-auctions/properties?company_id=31")
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["success"] is False
    assert "não habilitado" in payload["error"]


def test_financial_sheet_api_is_thin_and_tenant_scoped(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(route, "_resolve_company", lambda **kwargs: _company())

    def fake_upsert(company_id, property_id, payload):
        captured["sheet"] = {"company_id": company_id, "property_id": property_id, "payload": payload}
        return {"property_id": property_id, "winning_bid": payload["winning_bid"]}

    monkeypatch.setattr(route.RealEstateAuctionService, "upsert_financial_sheet", fake_upsert)

    response = app.test_client().put(
        "/api/real-estate-auctions/properties/44/financial-sheet?company_id=31",
        json={"winning_bid": "280000"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["financial_sheet"]["property_id"] == 44
    assert captured["sheet"]["company_id"] == 31
    assert captured["sheet"]["payload"] == {"winning_bid": "280000"}


def test_source_create_api_is_thin_and_tenant_scoped(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(route, "_resolve_company", lambda **kwargs: _company())

    def fake_create(company_id, payload):
        captured["source"] = {"company_id": company_id, "payload": payload}
        return {"id": 9, "company_id": company_id, "name": payload["name"]}

    monkeypatch.setattr(route.RealEstateAuctionService, "create_source", fake_create)

    response = app.test_client().post(
        "/api/real-estate-auctions/sources?company_id=31",
        json={"name": "Portal Caixa", "domain": "caixa.gov.br", "active": True},
    )
    payload = response.get_json()

    assert response.status_code == 201
    assert payload["success"] is True
    assert payload["source"]["company_id"] == 31
    assert captured["source"]["company_id"] == 31
    assert captured["source"]["payload"]["name"] == "Portal Caixa"


def test_app_registers_real_estate_auction_blueprint():
    source = open(r"C:\GestaoVersus\app32\app32\app.py", "r", encoding="utf-8").read()

    assert "from api.routes.real_estate_auctions import real_estate_auctions_bp" in source
    assert "app.register_blueprint(real_estate_auctions_bp)" in source


def test_sidebar_exposes_module_only_when_enabled():
    source = open(
        r"C:\GestaoVersus\app32\app32\templates\partials\sidebar_standard.html",
        "r",
        encoding="utf-8",
    ).read()

    assert "real_estate_auctions_enabled()" in source
    assert "has_permission('real_estate_auctions', 'view')" in source
    assert "/real-estate-auctions" in source


def test_rbac_catalog_contains_real_estate_auction_domain():
    assert "triage" in RbacPermissionCatalogService.action_keys()
    assert "manage_financial_sheet" in RbacPermissionCatalogService.action_keys()

    node = RbacPermissionCatalogService.node_map()["real_estate_auctions"]
    assert node["label"] == "Leilões Imobiliários"
    assert "configure" in node["actions"]
    assert RbacPermissionCatalogService.has_permission(
        {"real_estate_auctions": ["view", "create", "edit"]},
        "real_estate_auctions",
        "create",
    )
