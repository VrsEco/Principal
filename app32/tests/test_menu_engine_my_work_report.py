from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence import menu_engine


def test_resolve_period_relative_this_month(monkeypatch):
    monkeypatch.setattr(menu_engine, "_local_today", lambda: date(2026, 3, 5))

    start, end = menu_engine._resolve_period_from_payload({"periodo": "este mes"})

    assert start == date(2026, 3, 5)
    assert end == date(2026, 3, 31)


def test_resolve_period_relative_next_15_days(monkeypatch):
    monkeypatch.setattr(menu_engine, "_local_today", lambda: date(2026, 3, 5))

    start, end = menu_engine._resolve_period_from_payload({"periodo": "proximos 15 dias"})

    assert start == date(2026, 3, 5)
    assert end == date(2026, 3, 19)


def test_format_my_work_report_hierarchy_with_meetings_whatsapp(monkeypatch):
    monkeypatch.setattr(menu_engine, "_local_today", lambda: date(2026, 3, 5))
    monkeypatch.setattr(menu_engine, "_resolve_report_user_name", lambda user_id: "Fabiano")

    tasks = [
        {
            "company_id": 1,
            "company_code": "AL",
            "company_name": "Save Water",
            "project_code": "AL.J.4",
            "project_name": "Reuniao Semanal",
            "activity_code": "AL.J.4.97",
            "title": "Piramide de Vendas",
            "responsible": "Fabiano",
            "due_date": "2026-03-09",
            "completion_date": "-",
        }
    ]
    processes = [
        {
            "company_id": 1,
            "company_code": "AL",
            "company_name": "Save Water",
            "process_code": "AL.C.3.3.3",
            "process_name": "Financeiro",
            "instance_code": "AL.P95.001",
            "title": "Aprovacao de Contas a Pagar",
            "owner": "Marcel",
            "due_date": "2026-03-11",
            "completion_date": "-",
        }
    ]
    meetings = [
        {
            "company_id": 1,
            "company_code": "AL",
            "company_name": "Save Water",
            "meeting_code": "AL.R.12",
            "meeting_name": "Reuniao Operacional",
            "project_code": "AL.J.4",
            "project_name": "Reuniao Semanal",
            "scheduled_time": "14:30",
            "due_date": "2026-03-10",
            "completion_date": "-",
        }
    ]

    report = menu_engine._format_my_work_report(
        action="my_work.due_range",
        company_label="empresa AL - Save Water",
        tasks=tasks,
        processes=processes,
        meetings=meetings,
        start_date=date(2026, 3, 5),
        end_date=date(2026, 3, 19),
        channel="whatsapp",
        payload={},
        user_id=10,
    )

    assert "Resumo das atividades" in report
    assert "empresa AL - Save Water" in report
    assert "vencendo nos proximos 15 dias (05/03/2026 a 19/03/2026)" in report
    assert "*Empresa*" in report
    assert "*Projetos*" in report
    assert "AL.J.4 - Reuniao Semanal" in report
    assert "AL.J.4.97 - Piramide de Vendas" in report
    assert "*Processos*" in report
    assert "AL.C.3.3.3 - Financeiro" in report
    assert "AL.P95.001 - Aprovacao de Contas a Pagar" in report
    assert "*Reunioes Agendadas*" in report
    assert "AL.R.12 - Reuniao Operacional" in report
