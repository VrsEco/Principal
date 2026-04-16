import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.intents import RoutineConsultIntentFormBuilder


def test_routine_consult_form_builder_hydrates_today_personal_query():
    builder = RoutineConsultIntentFormBuilder()

    form, error = builder.build(
        action="routine.consult",
        payload={},
        active_company_id=9,
        channel="whatsapp",
        raw_text="Quais atividades tenho para hoje?",
    )

    assert error is None
    assert form is not None
    assert form.intent_code == "query.routine.consult"
    assert form.company_scope.company_ids == [9]
    assert form.filter_scope.period_label == "hoje"
    assert form.filter_scope.status == "open"
    assert form.filter_scope.entity_hint == "project_task"
    assert form.output_scope.format == "detailed_list"


def test_routine_consult_form_builder_marks_mixed_scope_for_processes_and_meetings():
    builder = RoutineConsultIntentFormBuilder()

    form, error = builder.build(
        action="routine.consult",
        payload={},
        active_company_id=None,
        channel="web",
        raw_text="Quais processos e reuniões tenho esta semana?",
    )

    assert error is None
    assert form is not None
    assert form.filter_scope.period_label == "esta semana"
    assert form.filter_scope.entity_hint == "mixed"
