import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.intents import (
    MyWorkIntentFormBuilder,
    OperationalIntentConfirmationPresenter,
    OperationalIntentDispatcher,
)


def test_my_work_intent_form_builder_generates_canonical_form():
    builder = MyWorkIntentFormBuilder()

    form, error = builder.build(
        action="my_work.open",
        payload={
            "_selected_company_id": 9,
            "colaborador": "Caroline Marques",
            "entidade": "project_task",
        },
        active_company_id=1,
        channel="whatsapp",
        raw_text="Quais as atividades em aberto para Caroline Marques?",
    )

    assert error is None
    assert form is not None
    assert form.intent_code == "query.my_work.open"
    assert form.company_scope.company_ids == [9]
    assert form.subject_scope.responsible_names == ["Caroline Marques"]
    assert form.filter_scope.entity_hint == "project_task"
    assert form.to_execution_payload()["_selected_company_id"] == 9


def test_my_work_intent_form_builder_marks_missing_period_for_due_range():
    builder = MyWorkIntentFormBuilder()

    form, error = builder.build(
        action="my_work.due_range",
        payload={"_selected_company_id": 9},
        active_company_id=None,
        channel="whatsapp",
        raw_text="O que temos para fazer?",
    )

    assert error is None
    assert form is not None
    assert form.resolution_scope.status == "missing_fields"
    assert form.resolution_scope.missing_fields == ["periodo"]


def test_operational_intent_confirmation_presenter_builds_readable_text():
    builder = MyWorkIntentFormBuilder()
    presenter = OperationalIntentConfirmationPresenter()
    form, _ = builder.build(
        action="my_work.overdue",
        payload={
            "_selected_company_id": 9,
            "colaborador": "Caroline Marques",
            "periodo": "esta semana",
            "entidade": "project_task",
        },
        active_company_id=None,
        channel="whatsapp",
        raw_text="Quais atividades atrasadas da Caroline esta semana?",
    )
    form.company_scope.company_labels = ["AU - Gandu Investimentos e Participações"]

    text = presenter.build_confirmation_text(form)

    assert "Caroline Marques" in text
    assert "AU - Gandu Investimentos e Participações" in text
    assert "Posso continuar?" in text


def test_operational_intent_dispatcher_resolves_action_key():
    builder = MyWorkIntentFormBuilder()
    dispatcher = OperationalIntentDispatcher(
        {
            "query.my_work.open": "my_work.open",
            "query.my_work.overdue": "my_work.overdue",
        }
    )
    form, _ = builder.build(
        action="my_work.open",
        payload={"_selected_company_id": 9},
        active_company_id=None,
        channel="web",
    )

    assert dispatcher.resolve_action_key(form) == "my_work.open"
