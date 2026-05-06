import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_execution_runtime_service import (
    _build_diagram_navigation,
    _format_runtime_url_template,
    apply_runtime_defaults,
    pause_instance,
    resume_instance,
    validate_execution_status,
    validate_instance_status,
)


def test_validate_instance_status_accepts_runtime_values():
    assert validate_instance_status("paused") == "paused"
    assert validate_instance_status("waiting_external") == "waiting_external"


def test_validate_execution_status_rejects_invalid_value():
    with pytest.raises(ValueError):
        validate_execution_status("not-valid")


def test_apply_runtime_defaults_populates_bpmn_context(monkeypatch):
    instance = SimpleNamespace(
        process_id=10,
        company_id=20,
        process_bpmn_diagram_id=None,
        process_version=None,
        current_bpmn_element_id=None,
        status="in_progress",
        started_at=None,
        completed_at=None,
    )

    monkeypatch.setattr(
        "services.process_execution_runtime_service.get_published_diagram_for_process",
        lambda **kwargs: SimpleNamespace(id=99, version=7),
    )
    monkeypatch.setattr(
        "services.process_execution_runtime_service.resolve_initial_bpmn_element_id",
        lambda **kwargs: "Activity_Initial",
    )

    apply_runtime_defaults(instance)

    assert instance.process_bpmn_diagram_id == 99
    assert instance.process_version == 7
    assert instance.current_bpmn_element_id == "Activity_Initial"
    assert instance.started_at is not None


def test_pause_and_resume_instance_updates_runtime_fields(monkeypatch):
    instance = SimpleNamespace(
        status="in_progress",
        paused_at=None,
        pause_reason=None,
        started_at=None,
    )

    monkeypatch.setattr("services.process_execution_runtime_service.db.session.flush", lambda: None)

    pause_instance(instance=instance, reason="Aguardando operador")
    assert instance.status == "paused"
    assert instance.paused_at is not None
    assert instance.pause_reason == "Aguardando operador"

    resume_instance(instance=instance)
    assert instance.status == "in_progress"
    assert instance.started_at is not None
    assert instance.paused_at is None
    assert instance.pause_reason is None


def test_build_diagram_navigation_returns_next_candidates():
    bpmn_xml = """
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
      <bpmn:process id="Process_1">
        <bpmn:startEvent id="StartEvent_1" name="Início" />
        <bpmn:userTask id="Task_1" name="Cadastrar contrato" />
        <bpmn:serviceTask id="Task_2" name="Gerar PDF" />
        <bpmn:sequenceFlow id="Flow_1" sourceRef="Task_1" targetRef="Task_2" />
      </bpmn:process>
    </bpmn:definitions>
    """

    navigation = _build_diagram_navigation(bpmn_xml, "Task_1")

    assert navigation["next_candidates"] == [{
        "element_id": "Task_2",
        "element_name": "Gerar PDF",
        "element_type": "serviceTask",
    }]


def test_format_runtime_url_template_replaces_context():
    assert _format_runtime_url_template(
        "/contracts/{contract_id}?company_id={company_id}&tab=cliente",
        {"contract_id": 17, "company_id": 9},
    ) == "/contracts/17?company_id=9&tab=cliente"
