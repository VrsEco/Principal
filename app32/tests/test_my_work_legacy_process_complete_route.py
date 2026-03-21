import os
import sys

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api.routes.my_work as my_work_module


def test_my_work_legacy_complete_uses_session_active_company(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "test"
    captured = {}

    monkeypatch.setattr(my_work_module, "current_user", type("User", (), {"id": 15})())

    def _fake_complete_process_instance_for_my_work(**kwargs):
        captured.update(kwargs)
        return {"success": True, "data": {"id": kwargs["instance_id"], "status": "completed"}}

    fake_service_module = type(
        "FakeServiceModule",
        (),
        {"complete_process_instance_for_my_work": staticmethod(_fake_complete_process_instance_for_my_work)},
    )()

    sys.modules["services.my_work.process_actions_service"] = fake_service_module

    with app.test_request_context(
        "/my-work/api/process-instances/56/complete",
        method="POST",
        json={"completion_comment": "ok"},
    ):
        from flask import session

        session["active_company_id"] = 2
        response, status_code = my_work_module.my_work_complete_process_instance_legacy.__wrapped__(56)

    body = response.get_json()
    assert status_code == 200
    assert body["success"] is True
    assert captured["user_id"] == 15
    assert captured["instance_id"] == 56
    assert captured["company_id"] == 2
    assert captured["completion_comment"] == "ok"
