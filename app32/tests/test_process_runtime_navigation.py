from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services.process_execution_runtime_service import (
    advance_instance_after_execution,
    calculate_execution_duration_seconds,
    resolve_initial_executable_activity,
    resolve_next_executable_candidates,
)


BPMN = """
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <process id="Process_1">
    <startEvent id="start"><outgoing>f1</outgoing></startEvent>
    <userTask id="task_a" name="Receber solicitação" />
    <exclusiveGateway id="decision" name="Aprovado?" />
    <userTask id="task_yes" name="Prosseguir" />
    <userTask id="task_no" name="Corrigir" />
    <endEvent id="end" />
    <sequenceFlow id="f1" sourceRef="start" targetRef="task_a" />
    <sequenceFlow id="f2" sourceRef="task_a" targetRef="decision" />
    <sequenceFlow id="f3" name="Sim" sourceRef="decision" targetRef="task_yes" />
    <sequenceFlow id="f4" name="Não" sourceRef="decision" targetRef="task_no" />
    <sequenceFlow id="f5" sourceRef="task_yes" targetRef="end" />
  </process>
</definitions>
"""


def test_resolves_initial_activity_from_published_graph():
    initial = resolve_initial_executable_activity(BPMN)

    assert initial["element_id"] == "task_a"
    assert initial["element_name"] == "Receber solicitação"


def test_calculates_duration_between_naive_and_timezone_aware_timestamps():
    started_at = datetime(2026, 8, 20, 14, 33, 55)
    completed_at = datetime(2026, 8, 20, 17, 34, 5, tzinfo=timezone.utc)

    assert calculate_execution_duration_seconds(started_at, completed_at) == 10810


def test_calculated_duration_is_never_negative():
    started_at = datetime.now(timezone.utc)
    completed_at = started_at - timedelta(seconds=5)

    assert calculate_execution_duration_seconds(started_at, completed_at) == 0


def test_resolves_executable_candidates_across_gateway():
    navigation = resolve_next_executable_candidates(BPMN, "task_a")

    assert navigation["source_found"] is True
    assert [(item["element_id"], item["path_label"]) for item in navigation["candidates"]] == [
        ("task_yes", "Sim"),
        ("task_no", "Não"),
    ]


def test_advance_requires_valid_branch_and_completes_at_end():
    diagram = SimpleNamespace(bpmn_xml=BPMN)
    instance = SimpleNamespace(
        process_id=5,
        company_id=10,
        current_bpmn_element_id="task_a",
        status="in_progress",
        completed_at=None,
    )
    execution = SimpleNamespace(bpmn_element_id="task_a")

    try:
        advance_instance_after_execution(instance=instance, execution=execution, diagram=diagram)
        assert False, "bifurcação deveria exigir escolha"
    except ValueError as exc:
        assert "Selecione" in str(exc)

    result = advance_instance_after_execution(
        instance=instance,
        execution=execution,
        diagram=diagram,
        requested_next_element_id="task_yes",
    )
    assert result["next_activity"]["element_id"] == "task_yes"
    assert instance.current_bpmn_element_id == "task_yes"

    result = advance_instance_after_execution(
        instance=instance,
        execution=SimpleNamespace(bpmn_element_id="task_yes"),
        diagram=diagram,
    )
    assert result["completed"] is True
    assert instance.status == "completed"
    assert instance.current_bpmn_element_id is None
