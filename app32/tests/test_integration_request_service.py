import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.integration_request_service import IntegrationRequestService


def test_integration_request_service_creates_slug_and_backlog(monkeypatch):
    added = []
    state = {"committed": False}

    session = SimpleNamespace(
        add=lambda item: added.append(item),
        flush=lambda: setattr(added[-1], "id", 77) if added else None,
        commit=lambda: state.__setitem__("committed", True),
    )

    monkeypatch.setattr("services.integration_request_service.db", SimpleNamespace(session=session))
    monkeypatch.setattr(
        "services.integration_request_service.ProjectTaskService.create_project_task",
        lambda **kwargs: ({"task": SimpleNamespace(id=456)}, None),
    )

    record = IntegrationRequestService.create_request(
        {
            "title": "Open Finance Banco X",
            "business_domain": "Financeiro",
            "integration_mode": "consume",
            "technical_channel": "api_mcp",
            "external_system": "Banco X",
            "objective": "Consumir extratos bancários para conciliação operacional.",
            "data_summary": "Extratos e saldos bancários.",
        },
        company_id=31,
        requester_user_id=9,
        requester_name="Fabiano",
    )

    assert record.slug == "open-finance-banco-x"
    assert record.backlog_task_id == 456
    assert state["committed"] is True
