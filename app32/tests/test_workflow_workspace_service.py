import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.workflow_workspace_service import WorkflowWorkspaceService


def test_workflow_workspace_service_groups_by_domain(monkeypatch):
    class _FakeColumn:
        def __eq__(self, _other):
            return self

        def is_(self, _other):
            return self

        def isnot(self, _other):
            return self

        def asc(self):
            return self

        def desc(self):
            return self

    class _FakeQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def filter_by(self, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    fake_option_model = type("FakeAgentMenuOption", (), {"query": _FakeQuery(), "company_id": _FakeColumn(), "sort_order": _FakeColumn(), "code": _FakeColumn()})
    fake_usage_model = type("FakeWorkflowExecutionLog", (), {"query": _FakeQuery(), "company_id": _FakeColumn(), "updated_at": _FakeColumn()})
    fake_gap_model = type("FakeWorkflowGapCandidate", (), {"query": _FakeQuery(), "company_id": _FakeColumn(), "created_at": _FakeColumn()})

    monkeypatch.setattr("services.workflow_workspace_service.AgentMenuOption", fake_option_model)
    monkeypatch.setattr("services.workflow_workspace_service.WorkflowExecutionLog", fake_usage_model)
    monkeypatch.setattr("services.workflow_workspace_service.WorkflowGapCandidate", fake_gap_model)
    monkeypatch.setattr("services.workflow_workspace_service.or_", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "services.workflow_workspace_service.build_workflow_catalog",
        lambda **kwargs: {
            "summary": {"workflow_count": 2},
            "workflows": [
                {"code": "1.4", "title": "Cadastrar Atividade", "parent_title": "Projetos", "is_active": True, "sort_order": 1},
                {"code": "1.5", "title": "Atualizar Atividade", "parent_title": "Projetos", "is_active": True, "sort_order": 2},
            ],
        },
    )

    payload = WorkflowWorkspaceService.build_catalog(SimpleNamespace(id=31))

    assert payload["summary"]["active_workflow_count"] == 2
    assert payload["domains"][0]["title"] == "Projetos"
    assert payload["domains"][0]["count"] == 2
