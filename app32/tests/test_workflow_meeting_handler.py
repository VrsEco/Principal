from datetime import date, datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    MeetingScheduleExecutionHandler,
    MeetingScheduleRequest,
    MeetingStartExecutionHandler,
    MeetingStartRequest,
    MeetingSummarizeExecutionHandler,
    MeetingSummarizeRequest,
)


class DummyCompany:
    def __init__(self, company_id: int, name: str, client_code: str = ""):
        self.id = company_id
        self.name = name
        self.client_code = client_code


class DummyMeeting:
    def __init__(self, meeting_id: int):
        self.id = meeting_id
        self.company_id = 9
        self.title = "Reuniao de Operacoes"
        self.status = "draft"
        self.project_id = None
        self.scheduled_date = date(2026, 3, 20)
        self.scheduled_time = "14:30"
        self.actual_date = None
        self.actual_time = None
        self.guests_json = None
        self.discussions_json = None
        self.activities_json = None
        self.meeting_notes = None


def _build_handler(**overrides):
    captured = {}

    def fake_resolve_company_ids_for_payload(payload, active_company_id, user_id):
        captured["resolved"] = {
            "payload": dict(payload or {}),
            "active_company_id": active_company_id,
            "user_id": user_id,
        }
        return [9], "empresa AA - Versus"

    def fake_parse_meeting_datetime_input(**kwargs):
        captured["parsed"] = dict(kwargs)
        return date(2026, 3, 20), "14:30", None

    def fake_create_draft_meeting(**kwargs):
        captured["create_kwargs"] = dict(kwargs)
        return DummyMeeting(55), None

    defaults = {
        "resolve_company_ids_for_payload": fake_resolve_company_ids_for_payload,
        "parse_meeting_datetime_input": fake_parse_meeting_datetime_input,
        "create_draft_meeting": fake_create_draft_meeting,
        "load_company_by_id": lambda company_id: DummyCompany(company_id, "Versus", "AA"),
    }
    defaults.update(overrides)
    return MeetingScheduleExecutionHandler(**defaults), captured


def _build_start_handler(**overrides):
    captured = {}
    meeting = DummyMeeting(55)

    def fake_load_meeting_by_id(meeting_id):
        captured["meeting_id"] = meeting_id
        return meeting

    def fake_ensure_linked_project(current_meeting, started_at):
        captured["started_at"] = started_at
        current_meeting.project_id = 88
        return None, None

    defaults = {
        "load_meeting_by_id": fake_load_meeting_by_id,
        "user_can_access_company": lambda user_id, company_id: True,
        "now_provider": lambda: datetime(2026, 3, 20, 14, 30),
        "ensure_linked_project": fake_ensure_linked_project,
        "commit_changes": lambda: captured.setdefault("committed", True),
        "rollback_changes": lambda: captured.setdefault("rolled_back", True),
        "load_company_by_id": lambda company_id: DummyCompany(company_id, "Versus", "AA"),
    }
    defaults.update(overrides)
    return MeetingStartExecutionHandler(**defaults), captured, meeting


def _build_summarize_handler(**overrides):
    meeting = DummyMeeting(55)
    defaults = {
        "load_meeting_by_id": lambda meeting_id: meeting,
        "user_can_access_company": lambda user_id, company_id: True,
    }
    defaults.update(overrides)
    return MeetingSummarizeExecutionHandler(**defaults), meeting


def test_meeting_schedule_handler_requires_title():
    handler, _ = _build_handler()

    result = handler.execute(
        MeetingScheduleRequest(
            payload={"data_hora": "20/03/2026 14:30"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei o titulo da reuniao. Informe no formato: titulo: Nome da Reuniao"


def test_meeting_schedule_handler_requires_single_company_scope():
    handler, _ = _build_handler(
        resolve_company_ids_for_payload=lambda payload, active_company_id, user_id: (
            [7, 8],
            "empresas vinculadas",
        )
    )

    result = handler.execute(
        MeetingScheduleRequest(
            payload={"titulo": "Reuniao de Operacoes", "data_hora": "20/03/2026 14:30"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == (
        "Encontrei mais de uma empresa no seu contexto. "
        "Informe no formato: empresa: NOME_DA_EMPRESA"
    )


def test_meeting_schedule_handler_returns_parse_error():
    handler, _ = _build_handler(
        parse_meeting_datetime_input=lambda **kwargs: (
            None,
            None,
            "Data/Hora invalida. Use DD/MM/AAAA HH:MM.",
        )
    )

    result = handler.execute(
        MeetingScheduleRequest(
            payload={"titulo": "Reuniao de Operacoes", "data_hora": "ontem de tarde"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Data/Hora invalida. Use DD/MM/AAAA HH:MM."


def test_meeting_schedule_handler_formats_success():
    handler, captured = _build_handler()

    result = handler.execute(
        MeetingScheduleRequest(
            payload={
                "titulo": "Reuniao de Operacoes",
                "data_hora": "20/03/2026 14:30",
                "convidados": "Fabiano, Marcel\nAna",
                "pauta": "Comercial;Financeiro",
                "observacoes": "Sala 2",
            },
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["resolved"]["active_company_id"] == 9
    assert captured["parsed"]["datetime_raw"] == "20/03/2026 14:30"
    assert captured["create_kwargs"]["company_id"] == 9
    assert captured["create_kwargs"]["title"] == "Reuniao de Operacoes"
    assert captured["create_kwargs"]["scheduled_date"] == date(2026, 3, 20)
    assert captured["create_kwargs"]["scheduled_time"] == "14:30"
    assert captured["create_kwargs"]["notes"] == "Sala 2"
    assert captured["create_kwargs"]["guest_dict"] == {
        "Fabiano": "Fabiano",
        "Marcel": "Marcel",
        "Ana": "Ana",
    }
    assert captured["create_kwargs"]["agenda"] == [
        {"title": "Comercial"},
        {"title": "Financeiro"},
    ]
    assert "Reuniao 'Reuniao de Operacoes' agendada com sucesso!" in result.response_text
    assert "- ID: 55" in result.response_text
    assert "- Empresa: AA - Versus" in result.response_text
    assert "- Data/Hora: 2026-03-20 14:30" in result.response_text
    assert "- Convidados: Fabiano, Marcel, Ana" in result.response_text
    assert "- Pauta: Comercial; Financeiro" in result.response_text


def test_meeting_start_handler_requires_meeting_reference():
    handler, _, _ = _build_start_handler()

    result = handler.execute(
        MeetingStartRequest(
            payload={},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "Nao encontrei o ID da reuniao. Informe no formato: id_reuniao: 123"


def test_meeting_start_handler_formats_success_and_links_project():
    handler, captured, meeting = _build_start_handler()

    result = handler.execute(
        MeetingStartRequest(
            payload={"id_reuniao": "55"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert captured["meeting_id"] == 55
    assert captured["committed"] is True
    assert meeting.status == "in_progress"
    assert meeting.actual_date == date(2026, 3, 20)
    assert meeting.actual_time == "14:30"
    assert meeting.project_id == 88
    assert "Reuniao 'Reuniao de Operacoes' iniciada com sucesso!" in result.response_text
    assert "- ID Reuniao: 55" in result.response_text
    assert "- Projeto vinculado: AA.J.88" in result.response_text


def test_meeting_start_handler_blocks_access_outside_context():
    meeting = DummyMeeting(55)
    meeting.company_id = 12
    handler, _, _ = _build_start_handler(
        load_meeting_by_id=lambda meeting_id: meeting,
        user_can_access_company=lambda user_id, company_id: False,
    )

    result = handler.execute(
        MeetingStartRequest(
            payload={"id_reuniao": "55"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert result.response_text == "A reuniao informada nao pertence ao contexto da empresa ativa."


def test_meeting_summarize_handler_builds_summary_with_points_and_activities():
    handler, meeting = _build_summarize_handler()
    meeting.status = "in_progress"
    meeting.project_id = 88
    meeting.actual_date = date(2026, 3, 20)
    meeting.actual_time = "14:35"
    meeting.guests_json = '{"Fabiano":"Fabiano","Marcel":"Marcel"}'
    meeting.discussions_json = (
        '[{"title":"Pipeline","decision":"Revisar metas","responsible":"Fabiano","deadline":"25/03/2026"}]'
    )
    meeting.activities_json = (
        '[{"title":"Atualizar CRM","responsible":"Marcel","deadline":"22/03/2026"}]'
    )

    result = handler.execute(
        MeetingSummarizeRequest(
            payload={"id_reuniao": "55"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "Resumo da reuniao ID 55 - Reuniao de Operacoes" in result.response_text
    assert "- Participantes: Fabiano, Marcel" in result.response_text
    assert "- Projeto vinculado: 88" in result.response_text
    assert "Principais pontos:" in result.response_text
    assert "1. Pipeline | Decisao: Revisar metas | Responsavel: Fabiano | Prazo: 25/03/2026" in result.response_text
    assert "Atividades registradas:" in result.response_text
    assert "1. Atualizar CRM | Responsavel: Marcel | Prazo: 22/03/2026" in result.response_text


def test_meeting_summarize_handler_falls_back_to_notes():
    handler, meeting = _build_summarize_handler()
    meeting.meeting_notes = "  Esta é uma ata resumida da reunião.  "

    result = handler.execute(
        MeetingSummarizeRequest(
            payload={"meeting_id": "55"},
            active_company_id=9,
            user_id=10,
        )
    )

    assert "Resumo registrado:" in result.response_text
    assert "Esta é uma ata resumida da reunião." in result.response_text
