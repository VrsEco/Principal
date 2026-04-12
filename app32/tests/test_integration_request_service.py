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


def test_ensure_catalog_backlog_tasks_creates_missing_cards(monkeypatch):
    created = []

    monkeypatch.setattr(
        "services.integration_request_service.IntegrationRequestService._find_catalog_backlog_task",
        lambda key: None,
    )
    monkeypatch.setattr(
        "services.integration_catalog_service.IntegrationCatalogService.get_integration",
        lambda key: {
            "open_finance": {
                "key": "open_finance",
                "title": "Open Finance",
                "category": "Financeiro",
                "integration_mode": "consume",
                "technical_channel": "api_mcp",
                "status": "planned",
                "summary": "Resumo Open Finance",
                "description": "Descrição",
                "use_cases": ["Extratos"],
                "activation_requirements": ["Homologação"],
            },
            "financial_data_api": {
                "key": "financial_data_api",
                "title": "Dados Financeiros do APP32",
                "category": "Financeiro",
                "integration_mode": "provide",
                "technical_channel": "api",
                "status": "planned",
                "summary": "Resumo Dados",
                "description": "Descrição",
                "use_cases": ["BI"],
                "activation_requirements": [],
            },
            "erp_accounting_bridge": {
                "key": "erp_accounting_bridge",
                "title": "ERP / Contábil",
                "category": "Backoffice",
                "integration_mode": "bidirectional",
                "technical_channel": "api_mcp",
                "status": "discovery",
                "summary": "Resumo ERP",
                "description": "Descrição",
                "use_cases": ["Sincronizar"],
                "activation_requirements": [],
            },
        }.get(key),
    )
    monkeypatch.setattr(
        "services.integration_request_service.ProjectTaskService.create_project_task",
        lambda **kwargs: (
            created.append(kwargs)
            or {"task": SimpleNamespace(id=100 + len(created), stage=kwargs["stage"], code=f"AA.J.31.{100 + len(created)}", created_at=None, updated_at=None, notes=kwargs.get("notes"))},
            None,
        ),
    )

    records = IntegrationRequestService.ensure_catalog_backlog_tasks(
        requester_user_id=9,
        requester_name="Fabiano",
    )

    assert len(created) == 3
    assert created[0]["stage"] == "pending"
    assert created[1]["stage"] == "pending"
    assert created[2]["stage"] == "inbox"
    assert {item["title"] for item in records} == {
        "Open Finance",
        "Dados Financeiros do APP32",
        "ERP / Contábil",
    }


def test_serialize_request_record_uses_backlog_stage_labels():
    record = SimpleNamespace(
        to_dict=lambda: {
            "id": 7,
            "title": "Open Finance",
            "status": "requested",
            "backlog_task_id": 456,
            "created_at": "2026-04-12T10:00:00",
            "updated_at": "2026-04-12T10:00:00",
        },
        backlog_task_id=456,
    )
    task = SimpleNamespace(
        id=456,
        stage="executing",
        code="AA.J.31.456",
        created_at=None,
        updated_at=None,
    )

    payload = IntegrationRequestService._serialize_request_record(record, {456: task})

    assert payload["status"] == "executing"
    assert payload["status_label"] == "Executando"
    assert payload["backlog_task_code"] == "AA.J.31.456"
