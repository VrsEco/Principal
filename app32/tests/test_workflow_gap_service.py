import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import workflow_gap_service as gap_service


def test_extract_candidate_codes_from_discovery_trace():
    telemetry = {
        "workflow_discovery": {
            "selected_code": "3.1",
            "top_matches": [
                {"code": "3.1", "score": 30},
                {"code": "3.2", "score": 22},
            ],
            "confidence": {"candidate_codes": ["3.1", "3.2", "3.3"]},
        }
    }

    codes = gap_service._extract_candidate_codes(telemetry)

    assert codes == ["3.1", "3.2", "3.3"]


def test_create_gap_candidate_persists_and_links_project_card(monkeypatch):
    events = []

    class FakeSession:
        def add(self, obj):
            events.append(("add", obj))
            if getattr(obj, "id", None) is None:
                obj.id = 501

        def flush(self):
            events.append(("flush", None))

        def commit(self):
            events.append(("commit", None))

        def rollback(self):
            events.append(("rollback", None))

    fake_db = SimpleNamespace(session=FakeSession())
    monkeypatch.setattr(gap_service, "db", fake_db)

    fake_task = SimpleNamespace(id=204, project_id=31, code="AA.J.31.204", notes="", logs=[])

    def fake_create_project_task(**kwargs):
        events.append(("project_task", kwargs))
        return {"task": fake_task}, None

    monkeypatch.setattr(gap_service.ProjectTaskService, "create_project_task", fake_create_project_task)

    gap = gap_service.WorkflowGapService.create_gap_candidate(
        user_id=3,
        company_id=9,
        channel="whatsapp",
        thread_id="wa_7199",
        request_text="Preciso da ocupação do usuário X nesta semana",
        response_text="Posso levantar manualmente estes dados.",
        telemetry={
            "workflow_discovery": {
                "strategy": "hybrid",
                "confidence": {"route": "no_match", "candidate_codes": ["3.1"]},
            }
        },
    )

    assert gap is not None
    assert gap.id == 501
    assert gap.app_task_id == 204
    assert gap.app_task_code == "AA.J.31.204"
    assert gap.matched_workflow_codes == ["3.1"]
    assert "Origem do radar de gaps" in fake_task.notes
    assert fake_task.logs[-1]["type"] == "workflow_gap_created"
    assert fake_task.logs[-1]["gap_id"] == 501
    assert any(kind == "project_task" for kind, _ in events)
    project_task_call = next(payload for kind, payload in events if kind == "project_task")
    assert project_task_call["project_code"] == "AA.J.31"
    assert project_task_call["stage"] == "inbox"
    assert "ocupação do usuário X" in project_task_call["description"]
    assert "Resposta atual entregue pela IA" in project_task_call["notes"]


def test_build_gap_task_notes_includes_resolution_taxonomy():
    notes = gap_service._build_gap_task_notes(
        request_text="Quero as atividades abertas da Ventana com os Responsável Márcio Simoes",
        telemetry={"workflow_gap": {"resolution_type": "entity_resolution_failed"}},
        response_text="Nao encontrei empresa para 'Ventana'.",
    )

    assert "Classificacao do gap: entity_resolution_failed" in notes


def test_reclassify_workflow_gap_candidates_updates_historical_taxonomy():
    gap_a = SimpleNamespace(
        resolution_type='resolved_by_ai',
        user_request_text='Ops! Mensagem automática de ausência. Deixe sua mensagem.',
        normalized_intent='ops mensagem automatica',
        channel='whatsapp',
        status='inbox',
        telemetry={},
        app_task_code='AA.J.31.301',
    )
    gap_b = SimpleNamespace(
        resolution_type='resolved_by_ai',
        user_request_text='Quais atividades em aberto da Ventana com responsável Márcio Simoes?',
        normalized_intent='quais atividades ventana',
        channel='whatsapp',
        status='inbox',
        telemetry={'workflow_discovery': {'confidence': {'route': 'ambiguous'}, 'candidate_count': 2}},
        app_task_code='AA.J.31.302',
    )

    report = gap_service.reclassify_workflow_gap_candidates([gap_a, gap_b], persist=False)

    assert report['processed'] == 2
    assert report['updated'] == 2
    assert gap_a.resolution_type == gap_service.WORKFLOW_GAP_NOISE_IGNORED
    assert gap_b.resolution_type == gap_service.WORKFLOW_GAP_AMBIGUOUS_NEEDS_CLARIFICATION
    assert gap_b.telemetry['workflow_gap']['consolidation_key'].startswith('whatsapp|ambiguous_needs_clarification|')


def test_build_workflow_gap_metrics_groups_duplicate_clusters():
    gap_a = SimpleNamespace(
        resolution_type='not_supported_workflow',
        user_request_text='Preciso saber o que tenho para hoje',
        normalized_intent='preciso saber o que tenho para hoje',
        channel='whatsapp',
        status='inbox',
        app_task_code='AA.J.31.401',
    )
    gap_b = SimpleNamespace(
        resolution_type='not_supported_workflow',
        user_request_text='Preciso saber o que tenho para hoje',
        normalized_intent='preciso saber o que tenho para hoje',
        channel='whatsapp',
        status='inbox',
        app_task_code='AA.J.31.402',
    )

    metrics = gap_service.build_workflow_gap_metrics([gap_a, gap_b])

    assert metrics['total'] == 2
    assert metrics['duplicate_cluster_count'] == 1
    assert metrics['duplicate_clusters'][0]['count'] == 2



def test_find_workflow_gap_by_task_prefers_task_id(monkeypatch):
    captured = {}

    class _FakeOrdered:
        def first(self):
            return "gap-1"

    class _FakeQuery:
        def filter_by(self, **kwargs):
            captured.update(kwargs)
            return self

        def order_by(self, *_args, **_kwargs):
            return _FakeOrdered()

    fake_gap_model = SimpleNamespace(
        query=_FakeQuery(),
        created_at=SimpleNamespace(desc=lambda: None),
    )
    monkeypatch.setattr(gap_service, 'WorkflowGapCandidate', fake_gap_model)

    result = gap_service.find_workflow_gap_by_task(task_id=204)

    assert result == 'gap-1'
    assert captured == {'app_task_id': 204}
