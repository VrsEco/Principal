from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.presenters import (
    ChatMessageBlock,
    WorkflowDisplayOption,
    build_confirmation_display_items,
    build_confirmation_text,
    build_missing_fields_prompt,
    build_my_work_report,
    build_operation_company_prompt,
    build_summary_collaborator_prompt,
    build_summary_company_prompt,
    build_summary_period_prompt,
    build_channel_capabilities,
    build_chat_contract_message,
    build_collaborator_occupancy_report,
    build_internal_error_message,
    build_menu_recovery_message,
    build_status_callout,
    format_channel_heading,
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

    assert "Confirme a operacao" in text
    assert "Fluxo selecionado: 5.1 - Diagnosticar Funcionamento" in text
    assert "item: objetivo: MELHORAR VENDAS" in text
    assert "responda 'sim'" in text.lower()


def test_confirmation_presenter_supports_whatsapp_heading():
    option = WorkflowDisplayOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
    )

    text = build_confirmation_text(
        option,
        {"codigo_projeto": "AA.J.17"},
        format_project_choice_line=lambda value: value,
        format_project_task_choice_line=lambda value: None,
        format_process_instance_choice_line=lambda value: None,
        format_meeting_choice_line=lambda value: None,
        format_objective_label=lambda value: value,
        channel="whatsapp",
    )

    assert "*Confirme a operacao*" in text
    assert "*Fluxo selecionado: 1.4 - Cadastrar Atividade de Projeto*" in text


def test_summary_company_presenter_sanitizes_telegram_labels():
    option = WorkflowDisplayOption(code="3.5.1", title="Hoje", action_key="summary.today")

    text = build_summary_company_prompt(
        option,
        [{"index": 1, "label": "AA <Versus> & Co"}],
        channel="telegram",
    )

    assert "AA &lt;Versus&gt; &amp; Co" in text


def test_missing_fields_and_company_prompt_support_channel_formatting():
    option = WorkflowDisplayOption(code="1.4", title="Cadastrar Atividade", action_key="project_task.create")

    fields_text = build_missing_fields_prompt(
        option,
        [{"key": "nome", "label": "Nome <Atividade>"}],
        {"empresa": "AA & Co"},
        channel="whatsapp",
    )
    company_text = build_operation_company_prompt(
        option,
        [{"index": 1, "label": "AA - Versus"}],
        channel="whatsapp",
    )

    assert "*1.4 - Cadastrar Atividade*" in fields_text
    assert "Escolha a empresa para continuar:" in company_text


def test_channel_presenter_treats_instagram_as_chat_family():
    caps = build_channel_capabilities('instagram')

    assert caps['channel'] == 'instagram'
    assert caps['family'] == 'chat'
    assert caps['supports_compact_cards'] is True
    assert caps['supports_markdown_heading'] is True


def test_channel_presenter_formats_instagram_heading_like_chat():
    assert format_channel_heading('Resumo V3', 'instagram') == '*Resumo V3*'


def test_channel_presenter_formats_telegram_heading_as_html_bold():
    assert format_channel_heading('Resumo V3', 'telegram') == '<b>Resumo V3</b>'


def test_conversation_presenter_builds_status_callout():
    assert build_status_callout('warning', 'Confirme antes de executar') == '⚠️ Confirme antes de executar'


def test_my_work_presenter_builds_executive_panel():
    text = build_my_work_report(
        action='my_work.open',
        company_label='empresa AA - Versus',
        tasks=[{
            'company_id': 9, 'company_code': 'AA', 'company_name': 'Versus',
            'project_code': 'AA.J.31', 'project_name': 'Workflow V3',
            'activity_code': 'AA.J.31.203', 'title': 'Fase 8.5', 'responsible': 'Fabiano', 'due_date': '2026-03-12'
        }],
        processes=[{
            'company_id': 9, 'company_code': 'AA', 'company_name': 'Versus',
            'process_code': 'AA.P.10', 'process_name': 'Onboarding',
            'instance_code': 'AA.P.10.001', 'title': 'Aprovar escopo', 'owner': 'Fabiano', 'due_date': '2026-03-13'
        }],
        meetings=[{
            'company_id': 9, 'company_code': 'AA', 'company_name': 'Versus',
            'meeting_code': 'AA.R.12', 'meeting_name': 'Ritual V3', 'project_code': 'AA.J.31', 'project_name': 'Workflow V3',
            'due_date': '2026-03-14', 'scheduled_time': '10:00'
        }],
        start_date=None,
        end_date=None,
        channel='whatsapp',
        payload={'empresa': 'Versus'},
        manager_name='Fabiano',
        reference_date=date(2026, 3, 8),
        format_date_br=lambda value: str(value),
    )

    assert '*Painel Executivo*' in text
    assert 'Total de itens: 3' in text
    assert 'Atividades: 1 | Processos: 1 | Reunioes: 1' in text
    assert 'Proximo passo:' in text
    assert 'AA.J.31.203 - Fase 8.5' in text


def test_my_work_presenter_builds_empty_state_report():
    text = build_my_work_report(
        action='my_work.open',
        company_label='empresa AA - Versus',
        tasks=[],
        processes=[],
        meetings=[],
        start_date=None,
        end_date=None,
        channel='web',
        payload={},
        manager_name='Fabiano',
        reference_date=date(2026, 3, 8),
        format_date_br=lambda value: str(value),
    )

    assert 'Nenhum item encontrado para o filtro informado.' in text
    assert 'Proximo passo:' in text


def test_collaborator_presenter_builds_next_step_block():
    text = build_collaborator_occupancy_report(
        collaborator_name='Fabiano',
        company_label='AA - Versus',
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 7),
        available_hours=40.0,
        process_hours_taken=10.0,
        project_hours_taken=8.0,
        project_hours_committed=12.0,
        channel='telegram',
        format_date_br=lambda value: str(value),
    )

    assert '<b>Ocupacao do Colaborador</b>' in text
    assert 'Proximo passo:' in text
    assert 'Horas disponiveis' in text


def test_error_presenter_builds_internal_error_for_telegram():
    text = build_internal_error_message(channel='telegram')

    assert '<b>Nao foi possivel concluir a solicitacao</b>' in text
    assert 'engenharia foi notificado' in text.lower()
    assert 'Proximo passo:' in text


def test_error_presenter_builds_menu_recovery_for_whatsapp():
    text = build_menu_recovery_message(channel='whatsapp')

    assert '*Nao consegui abrir o menu agora*' in text
    assert 'Tente novamente em alguns segundos.' in text
    assert 'Proximo passo:' in text


def test_chat_contract_renders_next_step_for_telegram():
    text = build_chat_contract_message(
        'Contrato de Chat',
        subtitle='Padrao unificado',
        channel='telegram',
        blocks=[
            ChatMessageBlock(kind='status', text='ℹ️ Contexto pronto'),
            ChatMessageBlock(kind='next_step', items=['Responda 1 para continuar.', 'Responda 0 para sair.']),
        ],
    )

    assert '<b>Contrato de Chat</b>' in text
    assert 'Padrao unificado' in text
    assert 'Proximo passo:' in text
    assert '→ Responda 1 para continuar.' in text
