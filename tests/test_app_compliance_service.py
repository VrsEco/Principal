import pytest
from flask import Flask, request

from services import app_compliance_service


def _create_test_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.secret_key = "test-key"

    @app.route("/dummy-route")
    def dummy_route():
        return "ok"

    return app


def _patch_catalog(monkeypatch, pages, elements):
    monkeypatch.setattr(
        app_compliance_service.UIReferenceServiceV2,
        "get_all_pages",
        staticmethod(lambda: pages),
    )
    monkeypatch.setattr(
        app_compliance_service.UIReferenceServiceV2,
        "get_elements_by_page",
        staticmethod(lambda code: elements.get(code, [])),
    )


def test_run_full_scan_returns_summary(monkeypatch):
    app = _create_test_app()
    pages = [
        {
            "page_code": "001",
            "page_name": "Dashboard",
            "page_route": "/dummy-route",
            "template_file": "base.html",
            "active": True,
        }
    ]
    elements = {"001": [{"element_code": "001", "element_name": "header", "active": True}]}
    _patch_catalog(monkeypatch, pages, elements)

    with app.app_context():
        service = app_compliance_service.AppComplianceService()
        relatorio = service.run(scope="full")

        assert relatorio["overview"]["total_pages"] == 1
        assert relatorio["overview"]["ok"] == 1
        assert relatorio["results"][0]["status"] == "ok"
        assert relatorio["test_context"]["company_id"] == app_compliance_service.AppComplianceService.DEFAULT_TEST_CONTEXT["company_id"]

        mensagem = service.format_message(relatorio, highlight_limit=1)
        assert "001" in mensagem

        preview = service.build_preview(relatorio)
        assert preview is not None
        assert preview["OK"] == 1


def test_run_specific_page_not_found(monkeypatch):
    app = _create_test_app()
    pages = [
        {
            "page_code": "002",
            "page_name": "Configurações",
            "page_route": "/dummy-route",
            "template_file": "base.html",
            "active": True,
        }
    ]
    elements = {"002": []}
    _patch_catalog(monkeypatch, pages, elements)

    with app.app_context():
        service = app_compliance_service.AppComplianceService()
        with pytest.raises(ValueError):
            service.run(scope="page", page_code="999")


def test_route_probe_adds_execution_check(monkeypatch):
    app = _create_test_app()
    pages = [
        {
            "page_code": "003",
            "page_name": "Painel",
            "page_route": "/dummy-route",
            "template_file": "base.html",
            "active": True,
        }
    ]
    elements = {"003": []}
    _patch_catalog(monkeypatch, pages, elements)

    with app.app_context():
        service = app_compliance_service.AppComplianceService()
        relatorio = service.run(scope="full", probe_routes=True, probe_user_id=1)
        checks = relatorio["results"][0]["checks"]
        assert any(check["item"] == "rota_execucao" for check in checks)


def test_dynamic_route_uses_context_and_reports_errors(monkeypatch):
    app = _create_test_app()

    @app.route("/company/<int:company_id>/identity/mvv")
    def dyn_route(company_id: int):
        return f"company {company_id}"

    @app.route("/failing-route")
    def failing_route():
        raise RuntimeError("project_activities missing")

    pages = [
        {
            "page_code": "010",
            "page_name": "Dynamic Page",
            "page_route": "/company/<int:company_id>/identity/mvv",
            "template_file": "base.html",
            "active": True,
        },
        {
            "page_code": "011",
            "page_name": "Failing Page",
            "page_route": "/failing-route",
            "template_file": "base.html",
            "active": True,
        },
    ]
    elements = {"010": [], "011": []}
    _patch_catalog(monkeypatch, pages, elements)

    with app.app_context():
        service = app_compliance_service.AppComplianceService()
        relatorio = service.run(scope="full", probe_routes=True, probe_user_id=1, test_context={"company_id": 42})
        dynamic_checks = relatorio["results"][0]["checks"]
        assert any(check["item"] == "rota_parametros" and "company_id=42" in check["detail"] for check in dynamic_checks)

        failing_checks = relatorio["results"][1]["checks"]
        assert any(check["item"] == "rota_execucao" and "RuntimeError" in check["detail"] for check in failing_checks)


def test_configured_actions_capture_failures(monkeypatch):
    app = _create_test_app()

    @app.route("/action-fail", methods=["POST"])
    def action_fail():
        payload = request.get_json() or {}
        if str(payload.get("company_id")) == "42":
            return "Erro ao vincular", 400
        return "ok"

    pages = [
        {
            "page_code": "050",
            "page_name": "Página com ação",
            "page_route": "/dummy-route",
            "template_file": "base.html",
            "active": True,
        }
    ]
    elements = {"050": []}
    _patch_catalog(monkeypatch, pages, elements)

    def _fake_actions_config(self):
        return {
            "050": [
                {
                    "description": "Vincular empresa para teste",
                    "method": "POST",
                    "path": "/action-fail",
                    "json": {"company_id": "{company_id}"},
                    "required_context": ["company_id"],
                    "expected_status": 200,
                }
            ]
        }

    monkeypatch.setattr(
        app_compliance_service.AppComplianceService,
        "_load_actions_config",
        _fake_actions_config,
    )

    with app.app_context():
        service = app_compliance_service.AppComplianceService()
        relatorio = service.run(
            scope="full",
            probe_routes=True,
            probe_user_id=1,
            test_context={"company_id": 42},
        )
        action_checks = relatorio["results"][0]["checks"]
        assert any(
            check["item"].startswith("acao:") and check["status"] == "fail"
            for check in action_checks
        )


def test_format_message_filters_severity(monkeypatch):
    app = _create_test_app()
    pages = [
        {
            "page_code": "100",
            "page_name": "A",
            "page_route": "/dummy-route",
            "template_file": "base.html",
            "active": True,
        }
    ]
    elements = {"100": []}
    _patch_catalog(monkeypatch, pages, elements)

    relatorio = {
        "scope": "full",
        "generated_at": "2025-11-30T00:00:00Z",
        "overview": {"total_pages": 1, "ok": 1, "warn": 1, "fail": 1},
        "results": [
            {"page_code": "1", "page_name": "OK", "status": "ok", "checks": []},
            {"page_code": "2", "page_name": "WARN", "status": "warn", "checks": []},
            {"page_code": "3", "page_name": "FAIL", "status": "fail", "checks": []},
        ],
    }

    with app.app_context():
        service = app_compliance_service.AppComplianceService()
        txt = service.generate_text_report(relatorio, severity="errors")
        assert "FAIL" in txt and "WARN" not in txt

        msg = service.format_message(relatorio, severity="warnings")
        assert "WARN" in msg and "FAIL" not in msg
