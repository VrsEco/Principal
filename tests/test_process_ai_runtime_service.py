import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_ai_runtime_service import (
    _apply_ai_result,
    _normalize_llm_result,
    should_auto_run_ai_execution,
)


def test_should_auto_run_ai_execution_rules():
    assert should_auto_run_ai_execution(execution_mode="ai_task", status="pending") is True
    assert should_auto_run_ai_execution(execution_mode="ai_decision", status="ready", trigger_on_update=True) is True
    assert should_auto_run_ai_execution(execution_mode="ai_decision", status="completed", trigger_on_update=True) is False
    assert should_auto_run_ai_execution(execution_mode="human_task", status="pending") is False


def test_normalize_llm_result_rejects_decision_outside_allowlist():
    result = _normalize_llm_result(
        {"success": True, "confidence": 0.95, "decision": "other", "data": {}},
        execution_mode="ai_decision",
        ai_config={"allowed_decisions": ["archive", "finance"]},
    )

    assert result["success"] is False
    assert "decision_outside_allowlist" in result["warnings"]


def test_apply_ai_result_completes_and_advances_single_next_candidate(monkeypatch):
    instance = SimpleNamespace(
        id=10,
        company_id=5,
        process_id=3,
        status="in_progress",
        completed_at=None,
        current_bpmn_element_id="Task_1",
        runtime_context_json={},
    )
    execution = SimpleNamespace(
        id=99,
        execution_mode="ai_task",
        bpmn_element_id="Task_1",
        started_at=None,
        completed_at=None,
        waiting_since=None,
        duration_seconds=None,
        request_payload_json={},
        response_payload_json={},
        error_payload_json={},
        metadata_json={},
        status="pending",
    )
    monkeypatch.setattr(
        "services.process_ai_runtime_service._build_next_candidates",
        lambda **kwargs: [{"element_id": "Task_2", "element_name": "Próxima", "element_type": "serviceTask"}] if kwargs["source_element_id"] == "Task_1" else [],
    )

    _apply_ai_result(
        instance=instance,
        execution=execution,
        contract=None,
        ai_config={"min_confidence": 0.8, "metadata": {"auto_advance": True}},
        result={"success": True, "confidence": 0.92, "decision": None, "data": {"amount": 12}},
    )

    assert execution.status == "completed"
    assert instance.current_bpmn_element_id == "Task_2"
    assert instance.status == "in_progress"


def test_apply_ai_result_routes_to_human_review_when_confidence_is_low():
    instance = SimpleNamespace(
        id=10,
        company_id=5,
        process_id=3,
        status="in_progress",
        completed_at=None,
        current_bpmn_element_id="Gateway_1",
        runtime_context_json={},
    )
    execution = SimpleNamespace(
        id=99,
        execution_mode="ai_decision",
        bpmn_element_id="Gateway_1",
        started_at=None,
        completed_at=None,
        waiting_since=None,
        duration_seconds=None,
        request_payload_json={},
        response_payload_json={},
        error_payload_json={},
        metadata_json={},
        status="pending",
    )

    _apply_ai_result(
        instance=instance,
        execution=execution,
        contract=None,
        ai_config={"min_confidence": 0.9, "fallback_action": "human_review", "metadata": {}},
        result={"success": True, "confidence": 0.4, "decision": "archive", "data": {}},
    )

    assert execution.status == "waiting_external"
    assert instance.status == "waiting_external"
