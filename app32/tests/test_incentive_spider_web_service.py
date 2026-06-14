import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.incentive_spider_web_service import IncentiveSpiderWebService
from services import incentive_spider_web_service as spider_service


class QueryStub:
    def __init__(self, rows):
        self.rows = rows

    def filter_by(self, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def outerjoin(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)


def model_stub(rows=None, **attrs):
    col = SimpleNamespace(is_=lambda value: object(), isnot=lambda value: object(), in_=lambda values: object())
    base_attrs = {
        "id": col,
        "company_id": col,
        "employee_id": col,
        "process_id": col,
        "project_id": col,
        "routine_id": col,
        "indicator_id": col,
        "activity_id": col,
        "process_instance_id": col,
        "is_active": col,
        "is_deleted": col,
        "status": col,
    }
    base_attrs.update(attrs)
    if rows is not None:
        base_attrs["query"] = QueryStub(rows)
    return SimpleNamespace(**base_attrs)


def test_spider_web_service_includes_routines_and_capacity(monkeypatch):
    employee = SimpleNamespace(id=10, name="Ana", department="Operações")
    process = SimpleNamespace(id=20, name="Atendimento", kanban_stage="stable", owner_employee_id=10, responsible_id=None)
    project = SimpleNamespace(id=30, name="Implantação", status="in_progress", progress=40, kpis=[])
    routine = SimpleNamespace(
        id=40,
        name="Conferência diária",
        process_id=20,
        schedule_type="daily",
        start_time="08:00",
        deadline_days=0,
        deadline_hours=4,
        score_weight=1,
    )
    indicator = SimpleNamespace(
        id=50,
        name="SLA de conferência",
        indicator_type="result",
        responsible_id=10,
        collaborators=[],
        process_id=None,
        project_id=None,
        source_module="routine",
        source_id=40,
        routine_id=40,
    )
    block = SimpleNamespace(
        id=60,
        employee_id=10,
        name="Bloco Operacional",
        block_mode="operational",
        start_time=SimpleNamespace(strftime=lambda fmt: "08:00"),
        end_time=SimpleNamespace(strftime=lambda fmt: "12:00"),
        accepted_item_types=["routine"],
    )
    routine_collaborator = SimpleNamespace(employee_id=10, routine_id=40)
    routine_binding = SimpleNamespace(employee_id=10, routine_id=40, block_id=60)

    monkeypatch.setattr(spider_service, "Employee", model_stub([employee]))
    monkeypatch.setattr(spider_service, "Process", model_stub([process]))
    monkeypatch.setattr(spider_service, "Project", model_stub([project]))
    monkeypatch.setattr(spider_service, "Routine", model_stub([routine]))
    monkeypatch.setattr(spider_service, "WorkJourneyBlock", model_stub([block]))
    monkeypatch.setattr(spider_service, "Indicator", model_stub([indicator]))
    monkeypatch.setattr(spider_service, "RoutineCollaborator", model_stub())
    monkeypatch.setattr(spider_service, "RoutineJourneyBinding", model_stub([routine_binding], block_id=object()))
    monkeypatch.setattr(spider_service, "IndicatorGoal", model_stub([]))
    monkeypatch.setattr(spider_service, "ProcessInstanceCollaborator", model_stub())
    monkeypatch.setattr(spider_service, "ProcessInstance", model_stub())
    monkeypatch.setattr(spider_service, "ProjectActivityCollaborator", model_stub())
    monkeypatch.setattr(spider_service, "ProjectTask", model_stub())

    def fake_session_query(*entities):
        first = entities[0]
        if first is spider_service.RoutineCollaborator:
            return QueryStub([routine_collaborator])
        if first is spider_service.RoutineJourneyBinding:
            return QueryStub([routine_binding])
        if first is spider_service.IndicatorGoal:
            return QueryStub([])
        if first is spider_service.ProcessInstanceCollaborator:
            return QueryStub([])
        if first is spider_service.ProjectActivityCollaborator:
            return QueryStub([])
        return QueryStub([])

    monkeypatch.setattr(spider_service.db.session, "query", fake_session_query)

    payload = IncentiveSpiderWebService.build_graph(1)

    nodes_by_id = {node["id"]: node for node in payload["nodes"]}
    assert nodes_by_id["routine_40"]["type"] == "routine"
    assert nodes_by_id["capacity_60"]["type"] == "capacity"
    assert {"source": "routine_40", "target": "proc_20", "label": "rotina do processo", "strength": "direct"} in payload["links"]
    assert {"source": "routine_40", "target": "capacity_60", "label": "alocada em bloco", "strength": "direct"} in payload["links"]
    assert payload["summary"]["by_type"]["routine"] == 1
    assert payload["summary"]["by_type"]["capacity"] == 1


def test_spider_web_template_uses_csp_compatible_d3_cdn():
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates", "modules", "incentives", "spider_web.html")
    )
    with open(template_path, encoding="utf-8") as handle:
        content = handle.read()

    assert "cdnjs.cloudflare.com/ajax/libs/d3" in content
    assert "https://d3js.org/d3.v7.min.js" not in content
    assert "data-value=\"routine\"" in content
    assert "data-value=\"capacity\"" in content
