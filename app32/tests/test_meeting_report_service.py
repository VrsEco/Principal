import os
import sys
from types import SimpleNamespace

from flask import Flask, render_template

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.meeting_report_service import build_meeting_report_context


def test_build_meeting_report_context_merges_attendees_and_computes_dates():
    meeting_data = {
        'title': 'Reunião XYZ',
        'status': 'completed',
        'project_title': 'Projeto Growth',
        'project_code': 'PG.10',
        'created_at': '2026-03-20T08:15:00',
        'scheduled_date': '2026-03-27',
        'scheduled_time': '09:30',
        'actual_date': '2026-03-27',
        'actual_time': '09:45',
        'actual_duration_minutes': 75,
        'guests': {
            'internal': [{'id': 7, 'name': 'Ana'}],
            'external': [{'name': 'Cliente XP', 'email': 'cliente@xp.com', 'whatsapp': '71999990000'}],
        },
        'participants': {
            'internal': [{'id': 7, 'name': 'Ana'}],
            'external': [{'name': 'Cliente XP'}],
        },
    }
    employees = [
        SimpleNamespace(
            id=7,
            company_id=1,
            status='active',
            name='Ana',
            email='ana@empresa.com',
            phone='7133334444',
            whatsapp='71911112222',
        )
    ]

    report = build_meeting_report_context(meeting_data, employees)

    assert report['title'] == 'Reunião XYZ'
    assert report['project_label'] == 'PG.10 - Projeto Growth'
    assert report['status_label'] == 'Concluída'
    assert report['dates']['scheduling']['items'][0]['value'] == '27/03/2026 às 09:30'
    assert report['dates']['scheduling']['items'][1]['value'] == '20/03/2026 às 08:15'
    assert report['dates']['execution']['items'][0]['value'] == '27/03/2026 às 09:45'
    assert report['dates']['execution']['items'][1]['value'] == '27/03/2026 às 11:00'
    assert report['counts'] == {'invited': 2, 'present': 2}

    attendees = {item['name']: item for item in report['participants']}

    assert attendees['Ana']['type_label'] == 'Colaborador'
    assert attendees['Ana']['email'] == 'ana@empresa.com'
    assert attendees['Ana']['phone'] == '(71) 3333-4444'
    assert attendees['Ana']['invited'] is True
    assert attendees['Ana']['present'] is True

    assert attendees['Cliente XP']['type_label'] == 'Externo'
    assert attendees['Cliente XP']['email'] == 'cliente@xp.com'
    assert attendees['Cliente XP']['phone'] == '(71) 99999-0000'
    assert attendees['Cliente XP']['invited'] is True
    assert attendees['Cliente XP']['present'] is True


def test_report_template_contains_new_report_sections():
    app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')))
    report = build_meeting_report_context(
        {
            'title': 'Reunião Estratégica',
            'status': 'in_progress',
            'scheduled_date': '2026-03-27',
            'scheduled_time': '14:00',
            'actual_date': '2026-03-27',
            'actual_time': '14:10',
            'actual_duration_minutes': 50,
            'guests': {'internal': [], 'external': []},
            'participants': {'internal': [], 'external': []},
        },
        [],
    )

    with app.app_context():
        html = render_template(
            'report_pdf.html',
            meeting={
                'agenda': [{'title': 'Financeiro'}],
                'activities': [],
                'discussions': [],
                'meeting_notes': '',
                'invite_notes': 'Levar indicadores atualizados.',
                'project_title': None,
                'project_code': None,
            },
            report=report,
            company={'name': 'Empresa Teste', 'logo_primary': None},
            generated_at='27/03/2026 18:00',
        )

    assert 'Ata de Reunião' in html
    assert 'Reunião Estratégica' in html
    assert 'Datas' in html
    assert 'Agendamento' in html
    assert 'Realização' in html
    assert 'Participantes' in html
    assert html.count('class="intro-meta-item"') == 2
    assert 'Versus Gestão Corporativa - Todos os Direitos Reservados;' in html
    assert 'Emitido em 27/03/2026 18:00' in html
