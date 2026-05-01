from types import SimpleNamespace

from models.project import Project, ProjectTask
from services.project_task_service import ProjectTaskService


class _FakeCompanyQuery:
    def __init__(self, companies):
        self._companies = companies

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._companies)


class _FakeProjectQuery:
    def __init__(self, project):
        self._project = project

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._project


class _FakeColumn:
    def in_(self, values):
        return values

    def __eq__(self, other):
        return other


def test_project_and_task_code_use_scoped_sequences(monkeypatch):
    monkeypatch.setattr(Project, "company_code", property(lambda self: "AA"))

    project = Project(id=1904, company_id=77, code_sequence=1, name="Projeto")
    task = ProjectTask(id=2401, project_id=1904, code_sequence=1, what="Atividade")
    task.project = project

    assert project.code == "AA.J.1"
    assert task.code == "AA.J.1.1"


def test_resolve_project_by_code_prefers_company_prefix_and_sequence(monkeypatch):
    companies = [
        SimpleNamespace(id=10, client_code="AA", name="Empresa AA"),
        SimpleNamespace(id=20, client_code="AB", name="Empresa AB"),
    ]
    resolved_project = SimpleNamespace(id=999, company_id=20, code_sequence=1)
    fake_company_model = SimpleNamespace(query=_FakeCompanyQuery(companies))
    fake_project_model = SimpleNamespace(
        query=_FakeProjectQuery(resolved_project),
        company_id=_FakeColumn(),
        code_sequence=_FakeColumn(),
    )

    monkeypatch.setattr("services.project_task_service.Company", fake_company_model)
    monkeypatch.setattr("services.project_task_service.Project", fake_project_model)

    project, error = ProjectTaskService.resolve_project_by_code(
        "AB.J.1",
        allowed_company_ids=None,
    )

    assert error is None
    assert project.company_id == 20
    assert project.code_sequence == 1


def test_parse_project_code_accepts_company_sequence_format():
    assert ProjectTaskService.parse_project_code("AA.J.1") == ("AA", 1)
    assert ProjectTaskService.parse_project_code("AB.J.35") == ("AB", 35)
