from types import SimpleNamespace
from services.my_work import discovery_service
from services import my_work_service

from flask import Flask, session

from api.routes import my_work as my_work_module


def _app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    return app


def _allow_active_company(monkeypatch, company_id=9):
    monkeypatch.setattr(my_work_module, "get_active_company_id", lambda: company_id)
    monkeypatch.setattr(my_work_module, "can_access_company", lambda candidate: candidate == company_id)


def test_my_work_rejects_query_tenant_different_from_active_session(monkeypatch):
    app = _app()
    _allow_active_company(monkeypatch)

    with app.test_request_context("/my-work/api/activities?company_ids=22&active_company_id=22"):
        response, status = my_work_module.my_work_api_activities.__wrapped__()

    assert status == 403
    assert "não corresponde" in response.get_json()["error"]


def test_my_work_activities_scope_service_to_active_company(monkeypatch):
    app = _app()
    _allow_active_company(monkeypatch)
    monkeypatch.setattr(my_work_module, "current_user", SimpleNamespace(id=15))
    captured = {}

    def get_user_activities_v2(**kwargs):
        captured.update(kwargs)
        return [], {"me": 0, "company": 0, "general": 0}

    monkeypatch.setattr(discovery_service, "get_user_activities_v2", get_user_activities_v2)
    monkeypatch.setattr(my_work_service, "_calculate_stats_from_activities", lambda rows: {"total": len(rows)})

    with app.test_request_context("/my-work/api/activities?company_ids=9&active_company_id=9"):
        response = my_work_module.my_work_api_activities.__wrapped__()

    assert response.status_code == 200
    assert captured["company_ids"] == [9]
    assert captured["active_company_id"] == 9


def test_my_work_legacy_complete_rejects_payload_tenant_mismatch(monkeypatch):
    app = _app()
    _allow_active_company(monkeypatch)
    monkeypatch.setattr(my_work_module, "current_user", SimpleNamespace(id=15))

    with app.test_request_context(
        "/my-work/api/process-instances/56/complete",
        method="POST",
        json={"company_id": 22},
    ):
        session["active_company_id"] = 9
        response, status = my_work_module.my_work_complete_process_instance_legacy.__wrapped__(56)

    assert status == 403
    assert "não corresponde" in response.get_json()["error"]


def test_my_work_filter_options_requests_only_active_company(monkeypatch):
    app = _app()
    _allow_active_company(monkeypatch)
    monkeypatch.setattr(my_work_module, "current_user", SimpleNamespace(id=15))
    captured = {}

    def get_filter_options_v2(user_id, active_company_id=None):
        captured["user_id"] = user_id
        captured["active_company_id"] = active_company_id
        return {"companies": [], "collaborators": [], "user_role": "collaborator"}

    monkeypatch.setattr(discovery_service, "get_filter_options_v2", get_filter_options_v2)

    with app.test_request_context("/my-work/api/filter-options"):
        response = my_work_module.my_work_filter_options.__wrapped__()

    assert response.status_code == 200
    assert captured == {"user_id": 15, "active_company_id": 9}


def test_my_work_filter_directory_keeps_only_active_company(monkeypatch):
    monkeypatch.setattr(
        discovery_service,
        "User",
        SimpleNamespace(query=SimpleNamespace(get=lambda user_id: SimpleNamespace(id=user_id, role="collaborator"))),
    )
    monkeypatch.setattr(
        discovery_service,
        "_get_active_associated_companies",
        lambda user_id: [
            {"company_id": 9, "employee_id": 90, "employee_name": "Ana", "is_active": True},
            {"company_id": 22, "employee_id": 220, "employee_name": "Bia", "is_active": True},
        ],
    )
    monkeypatch.setattr(discovery_service, "_normalize_user_role", lambda *_args: "collaborator")
    monkeypatch.setattr(
        discovery_service,
        "fetch_project_directory",
        lambda company_ids: [{"id": 1, "company_id": company_ids[0]}],
    )
    monkeypatch.setattr(
        discovery_service,
        "fetch_process_directory",
        lambda company_ids: [{"id": 2, "company_id": company_ids[0]}],
    )

    payload = discovery_service.get_filter_options_v2(15, active_company_id=9)

    assert [item["company_id"] for item in payload["companies"]] == [9]
    assert [item["company_id"] for item in payload["collaborators"]] == [9]
    assert [item["company_id"] for item in payload["projects"]] == [9]
    assert [item["company_id"] for item in payload["processes"]] == [9]
