import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import project_responsible_summary_service as svc


def test_build_task_summary_payload_contains_5w1h():
    project = SimpleNamespace(code='AC.J.7', name='Projeto Alpha')
    task = SimpleNamespace(
        id=11,
        code='AC.J.7.11',
        what='Implantar painel executivo',
        due_date='2026-03-20',
        how='Executar via sprints semanais',
        status='in_progress',
        stage='executing',
        priority='high',
        estimated_hours=12,
        worked_hours=4,
        employee_name='Fabiano Ferreira',
        who='Fabiano Ferreira',
        project=project,
    )

    payload = svc._build_task_summary_payload(task)

    assert payload['subject'] == 'Resumo da Atividade - AC.J.7.11'
    assert '5W1H da atividade:' in payload['body']
    assert '- O que: Implantar painel executivo' in payload['body']
    assert '- Quem: Fabiano Ferreira' in payload['body']
    assert '- Onde: AC.J.7 - Projeto Alpha' in payload['body']
    assert '- Como: Executar via sprints semanais' in payload['body']


def test_build_project_summary_payload_lists_stats_and_tasks():
    tasks = [
        SimpleNamespace(
            id=11,
            code='AC.J.7.11',
            what='Implantar painel executivo',
            due_date='2026-03-20',
            stage='executing',
            status='in_progress',
            employee_name='Fabiano Ferreira',
            who='Fabiano Ferreira',
        ),
        SimpleNamespace(
            id=12,
            code='AC.J.7.12',
            what='Validar indicadores',
            due_date='2026-03-22',
            stage='pending',
            status='planned',
            employee_name='Maria Souza',
            who='Maria Souza',
        ),
    ]

    class _TaskQuery:
        def order_by(self, *args, **kwargs):
            return self
        def all(self):
            return tasks

    project = SimpleNamespace(
        id=7,
        code='AC.J.7',
        name='Projeto Alpha',
        owner='Fabiano Ferreira',
        status='in_progress',
        deadline='2026-03-31',
        task_stats={'total': 2, 'open': 2, 'completed': 0, 'delayed': 1, 'progress': 10},
        tasks=_TaskQuery(),
    )

    payload = svc._build_project_summary_payload(project)

    assert payload['subject'] == 'Resumo do Projeto - AC.J.7 - Projeto Alpha'
    assert 'Panorama do projeto:' in payload['body']
    assert '- Total: 2' in payload['body']
    assert '- Em aberto: 2' in payload['body']
    assert 'Atividades priorizadas:' in payload['body']
    assert '1. AC.J.7.11 | Implantar painel executivo' in payload['body']
    assert '2. AC.J.7.12 | Validar indicadores' in payload['body']


def test_build_project_summary_payload_lists_all_project_tasks():
    tasks = [
        SimpleNamespace(
            id=index,
            code=f'AX.J.31.{index}',
            what=f'Atividade {index}',
            due_date='2026-08-04',
            status='in_progress',
            employee_name='Fabiano Ferreira',
            who='Fabiano Ferreira',
        )
        for index in range(1, 12)
    ]

    class _TaskQuery:
        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return tasks

    project = SimpleNamespace(
        id=166,
        code='AX.J.31',
        name='Atividades Gerais',
        owner='Fabiano Ferreira',
        status='planned',
        deadline='2026-08-04',
        task_stats={'total': 11, 'open': 11, 'completed': 0, 'delayed': 0, 'progress': 0},
        tasks=_TaskQuery(),
    )

    payload = svc._build_project_summary_payload(project)

    assert '1. AX.J.31.1 | Atividade 1' in payload['body']
    assert '11. AX.J.31.11 | Atividade 11' in payload['body']
