import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.presenters import (
    WorkflowDisplayOption,
    build_confirmation_display_items,
    build_confirmation_text,
    build_summary_collaborator_prompt,
    build_summary_period_prompt,
)


def test_summary_presenter_builds_period_prompt():
    option = WorkflowDisplayOption(code="3.5.4", title="Personalizado", action_key="summary.custom")

    text = build_summary_period_prompt(option)

    assert "3.5.4 - Personalizado" in text
    assert "DD/MM/AAAA a DD/MM/AAAA" in text


def test_summary_presenter_builds_collaborator_prompt():
    option = WorkflowDisplayOption(code="3.5.1", title="Hoje", action_key="summary.today")

    text = build_summary_collaborator_prompt(
        option,
        [
            {"index": 1, "label": "Fulano"},
            {"index": 2, "label": "Beltrano"},
        ],
    )

    assert "0 - Todos os colaboradores" in text
    assert "1 - Fulano" in text
    assert "2 - Beltrano" in text


def test_confirmation_presenter_formats_project_task_create():
    option = WorkflowDisplayOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
    )

    items = build_confirmation_display_items(
        option,
        {
            "codigo_projeto": "AA.J.17",
            "nome_atividade": "Configurar dashboards",
        },
        format_project_choice_line=lambda value: f"{value} - Projeto V3",
        format_project_task_choice_line=lambda value: None,
        format_process_instance_choice_line=lambda value: None,
        format_meeting_choice_line=lambda value: None,
        format_objective_label=lambda value: value,
    )

    assert items[0] == "AA.J.17 - Projeto V3"
    assert "nome_atividade: Configurar dashboards" in items


def test_confirmation_presenter_builds_text():
    option = WorkflowDisplayOption(
        code="5.1",
        title="Diagnosticar Funcionamento",
        action_key="onboarding.diagnose",
    )

    text = build_confirmation_text(
        option,
        {"objetivo": "melhorar vendas"},
        format_project_choice_line=lambda value: None,
        format_project_task_choice_line=lambda value: None,
        format_process_instance_choice_line=lambda value: None,
        format_meeting_choice_line=lambda value: None,
        format_objective_label=lambda value: value.upper(),
    )

    assert "Confirme que voce quer:" in text
    assert "5.1 - Diagnosticar Funcionamento" in text
    assert "- objetivo: MELHORAR VENDAS" in text
    assert "responda 'sim'" in text.lower()
