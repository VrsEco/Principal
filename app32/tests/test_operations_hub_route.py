import os
import sys
from types import SimpleNamespace

from flask import Flask, render_template
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import main as main_route


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

    app.register_blueprint(main_route.main_bp)
    return app


def test_operations_hub_renders_unified_menu(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(
        main_route,
        "_resolve_active_company",
        lambda: SimpleNamespace(id=9, name="GanduInvest", client_code="GND"),
    )
    monkeypatch.setattr(
        main_route,
        "render_template",
        lambda template_name, **context: (
            captured.update(
                {
                    "payload": {
                        "template_name": template_name,
                        "context": context,
                    }
                }
            )
            or "ok"
        ),
    )

    client = app.test_client()
    response = client.get("/operations")

    assert response.status_code == 200
    assert captured["payload"]["template_name"] == "modules/operations/hub.html"
    modules = captured["payload"]["context"]["modules"]
    assert any(module["label"] == "Gestão Financeira" for module in modules)
    assert any(
        item["href"] == "/financial/accountability"
        for module in modules
        for group in module["groups"]
        for item in group["items"]
    )
    assert any(module["label"] == "Plataforma IA" for module in modules)

    assert any(
        item["href"] == "/financial/classification-dashboard"
        for module in modules
        for group in module["groups"]
        for item in group["items"]
    )
    assert any(
        item["href"] == "/financial/classification-rules"
        for module in modules
        for group in module["groups"]
        for item in group["items"]
    )
    assert any(
        item["href"] == "/financial/automation-rules"
        for module in modules
        for group in module["groups"]
        for item in group["items"]
    )


def test_operations_hub_template_renders_group_items_without_dict_method_collision():
    app = _build_app()

    with app.test_request_context("/operations"):
        html = render_template(
            "modules/operations/hub.html",
            active_company=SimpleNamespace(id=9, name="GanduInvest", client_code="GND"),
            modules=[
                {
                    "key": "financial",
                    "label": "Gestão Financeira",
                    "description": "Desc",
                    "groups": [
                        {
                            "label": "Grupo",
                            "items": [
                                {
                                    "title": "Prestação de contas",
                                    "description": "Desc",
                                    "href": "/financial/accountability",
                                    "mode": "Assistida",
                                }
                            ],
                        }
                    ],
                }
            ],
        )

    assert "Operações Inteligentes" in html
    assert "/financial/accountability" in html
    assert "Central inteligente" in html
