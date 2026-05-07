import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_execution_runtime_service import (
    _build_current_activity_action,
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


def test_build_current_activity_action_exposes_ai_summary():
    instance = SimpleNamespace(
        id=55,
        company_id=9,
        process_id=3,
        current_bpmn_element_id="Gateway_Review",
        runtime_context_json={"contract_id": 17},
    )
    contract = SimpleNamespace(
        execution_mode="ai_decision",
        capability_key="finance.route_document",
        route_name=None,
        interaction_mode="shell",
        auto_service_key="process.ai.route",
        requires_human_gate=True,
        allows_pause=True,
        allows_retry=True,
        sla_minutes=15,
        ui_schema_json={},
        rest_config_json={},
        mcp_config_json={},
        ai_config_json={
            "instruction": "Escolha entre archive ou finance.",
            "allowed_decisions": ["archive", "finance"],
            "tool_source": "mcp",
            "allowed_tools": ["finance.insert_prelaunch"],
        },
    )

    action = _build_current_activity_action(instance, contract, execution=None, element_id="Gateway_Review")

    assert action["execution_mode"] == "ai_decision"
    assert action["ai_enabled"] is True
    assert action["ai_summary"]["allowed_decisions"] == ["archive", "finance"]
    assert action["action_label"] == "Executar decisão com IA"


def test_build_current_activity_action_exposes_form_and_page_routes():
    instance = SimpleNamespace(
        id=77,
        company_id=9,
        process_id=3,
        current_bpmn_element_id="Task_Form",
        runtime_context_json={"document_id": 51},
    )
    form_contract = SimpleNamespace(
        execution_mode="open_form",
        capability_key="process.open_form",
        route_name=None,
        interaction_mode="drawer",
        auto_service_key="process.open_form",
        requires_human_gate=False,
        allows_pause=True,
        allows_retry=True,
        sla_minutes=None,
        ui_schema_json={"form_code": "financial_review", "prefill_mapping": {"document_id": "{document_id}"}},
        rest_config_json={},
        mcp_config_json={},
        ai_config_json={},
    )
    page_contract = SimpleNamespace(
        execution_mode="open_app32_page",
        capability_key="process.open_app32_page",
        route_name=None,
        interaction_mode="page",
        auto_service_key="process.open_app32_page",
        requires_human_gate=False,
        allows_pause=True,
        allows_retry=True,
        sla_minutes=None,
        ui_schema_json={"page_code": "finance_prelaunch_editor", "params_mapping": {"document_id": "{document_id}"}},
        rest_config_json={},
        mcp_config_json={},
        ai_config_json={},
    )

    form_action = _build_current_activity_action(instance, form_contract, execution=None, element_id="Task_Form")
    page_action = _build_current_activity_action(instance, page_contract, execution=None, element_id="Task_Page")

    assert form_action["internal_url"] == "/app32/forms/financial_review?document_id=51"
    assert form_action["executor_summary"]["open_form"] is True
    assert page_action["internal_url"] == "/app32/page/finance_prelaunch_editor?document_id=51"
    assert page_action["executor_summary"]["open_app32_page"] is True
