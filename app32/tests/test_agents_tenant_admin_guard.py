from types import SimpleNamespace

from flask import Flask, session

from api.routes import agents as agents_route


def _app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    return app


def _install_action(monkeypatch, action):
    import models.agent_action as agent_action_module

    monkeypatch.setattr(
        agent_action_module,
        "AgentAction",
        type("FakeAgentAction", (), {"query": SimpleNamespace(get=lambda action_id: action)}),
    )


def test_technical_repair_requires_platform_administrator(monkeypatch):
    app = _app()
    action = SimpleNamespace(id=17, type="technical_fix", company_id=9)
    _install_action(monkeypatch, action)
    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=8, role="user"))

    import services.engineering_service as engineering_module
    monkeypatch.setattr(
        engineering_module,
        "engineering_service",
        SimpleNamespace(execute_repair=lambda _action_id: (_ for _ in ()).throw(AssertionError("não deve executar"))),
    )

    with app.test_request_context("/api/agents/actions/approve/17", method="POST"):
        session["active_company_id"] = 9
        response, status = agents_route.approve_action.__wrapped__(17)

    assert status == 403
    assert "administradores da plataforma" in response.get_json()["error"]


def test_rollback_rejects_action_from_another_tenant_before_service(monkeypatch):
    app = _app()
    action = SimpleNamespace(id=17, type="technical_fix", company_id=22)
    _install_action(monkeypatch, action)
    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, role="admin"))

    import services.engineering_service as engineering_module
    monkeypatch.setattr(
        engineering_module,
        "engineering_service",
        SimpleNamespace(rollback_repair=lambda _action_id: (_ for _ in ()).throw(AssertionError("não deve executar"))),
    )

    with app.test_request_context("/api/agents/actions/rollback/17", method="POST"):
        session["active_company_id"] = 9
        response, status = agents_route.rollback_action.__wrapped__(17)

    assert status == 403
    assert "não pertence" in response.get_json()["error"]


def test_menu_listing_rejects_query_tenant_mismatch(monkeypatch):
    app = _app()

    with app.test_request_context("/api/agents/menu/options?company_id=22"):
        session["active_company_id"] = 9
        response, status = agents_route.list_agent_menu_options.__wrapped__()

    assert status == 403
    assert "não corresponde" in response.get_json()["error"]


def test_agent_catalog_is_not_exposed_to_regular_user(monkeypatch):
    app = _app()
    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=8, role="user"))

    with app.test_request_context("/api/agents"):
        response, status = agents_route.list_agents.__wrapped__()

    assert status == 403
    assert "administradores da plataforma" in response.get_json()["error"]


def test_menu_update_rejects_option_from_another_tenant(monkeypatch):
    app = _app()
    option = SimpleNamespace(id=7, company_id=22)
    _install_menu_option(monkeypatch, option)
    monkeypatch.setattr(agents_route, "current_user", SimpleNamespace(id=7, role="admin"))

    with app.test_request_context("/api/agents/menu/options/7", method="PATCH", json={"title": "Novo"}):
        session["active_company_id"] = 9
        response, status = agents_route.update_agent_menu_option.__wrapped__(7)

    assert status == 403
    assert "não pertence" in response.get_json()["error"]


def _install_menu_option(monkeypatch, option):
    import models.agent_menu as agent_menu_module

    monkeypatch.setattr(
        agent_menu_module,
        "AgentMenuOption",
        type("FakeMenuOption", (), {"query": SimpleNamespace(get=lambda option_id: option)}),
    )
