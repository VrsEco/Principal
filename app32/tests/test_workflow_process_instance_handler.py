from datetime import date, datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    ProcessInstanceCompleteExecutionHandler,
    ProcessInstanceCompleteRequest,
)


class DummyCompany:
    def __init__(self, client_code: str, name: str):
        self.client_code = client_code
        self.name = name


class DummyProcessInstance:
    def __init__(self):
        self.id = 95
        self.company_id = 9
        self.process_id = 3
        self.instance_code = "AA.P95.001"
        self.title = "Aprovacao Financeira"
        self.status = "in_progress"
        self.actual_end_date = None
        self.completed_at = None


def _build_handler(**overrides):
    captured = {}
    instance = DummyProcessInstance()

    def fake_commit_changes():
        captured["commits"] = captured.get("commits", 0) + 1

    defaults = {
        "extract_id_from_code": lambda code: 95 if code == "AA.P95.001" else None,
        "parse_completion_date": lambda raw: date(2026, 3, 22) if raw == "22/03/2026" else None,
        "today_provider": lambda: date(2026, 3, 23),
        "load_instance_by_id": lambda instance_id: instance if instance_id == 95 else None,
        "load_company_by_id": lambda company_id: DummyCompany("AA", "Versus"),
        "user_can_access_company": lambda user_id, company_id: True,
        "commit_changes": fake_commit_changes,
    }
    defaults.update(overrides)
    return ProcessInstanceCompleteExecutionHandler(**defaults), captured, instance


def test_process_instance_complete_handler_requires_instance_code():
    handler, _, _ = _build_handler()

    result = handler.execute(
        ProcessInstanceCompleteRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei o codigo da instancia. Informe no formato: codigo_instancia: CODIGO"


def test_process_instance_complete_handler_formats_success():
    handler, captured, instance = _build_handler()

    result = handler.execute(
        ProcessInstanceCompleteRequest(
            payload={"codigo_instancia": "AA.P95.001", "data_finalizacao": "22/03/2026"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["commits"] == 1
    assert instance.status == "completed"
    assert instance.actual_end_date == date(2026, 3, 22)
    assert instance.completed_at == datetime(2026, 3, 22, 0, 0)
    assert "AA.P95.001" in result.response_text
    assert "Aprovacao Financeira" in result.response_text
    assert "Data de Conclusao: 2026-03-22" in result.response_text


def test_process_instance_complete_handler_blocks_access_outside_context():
    handler, _, instance = _build_handler(
        user_can_access_company=lambda user_id, company_id: False,
    )
    instance.company_id = 12

    result = handler.execute(
        ProcessInstanceCompleteRequest(
            payload={"codigo_instancia": "AA.P95.001"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "A instancia informada nao pertence ao contexto da empresa ativa."
