from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.project_task_service as project_task_module
from services.project_task_service import ProjectTaskService


class _Company:
    def __init__(self, company_id: int, client_code: str, name: str = ""):
        self.id = company_id
        self.client_code = client_code
        self.name = name or client_code


class _Project:
    def __init__(self, project_id: int, company_id: int, code_sequence: int):
        self.id = project_id
        self.company_id = company_id
        self.code_sequence = code_sequence


class _CompanyQueryStub:
    def __init__(self, companies):
        self._companies = list(companies)

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._companies)


class _ProjectQueryStub:
    def __init__(self, project):
        self._project = project

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._project


class _Column:
    def in_(self, other):
        return ("in", tuple(other))

    def __eq__(self, other):
        return ("eq", other)


class _FakeCompanyModel:
    id = _Column()
    query = None


class _FakeProjectModel:
    company_id = _Column()
    code_sequence = _Column()
    query = None


def test_resolve_project_by_code_rejects_company_prefix_mismatch_even_with_single_allowed_company(monkeypatch):
    fake_company_model = type(
        "FakeCompanyModel",
        (_FakeCompanyModel,),
        {"query": _CompanyQueryStub([_Company(company_id=4, client_code="AL", name="Alpha Labs")])},
    )
    fake_project_model = type(
        "FakeProjectModel",
        (_FakeProjectModel,),
        {"query": _ProjectQueryStub(_Project(project_id=101, company_id=4, code_sequence=1))},
    )
    monkeypatch.setattr(project_task_module, "Company", fake_company_model)
    monkeypatch.setattr(project_task_module, "Project", fake_project_model)

    project, error = ProjectTaskService.resolve_project_by_code(
        "M1.J.1",
        allowed_company_ids=[4],
    )

    assert project is None
    assert error == "Empresa do código 'M1.J.1' não encontrada no contexto informado."


def test_resolve_project_by_code_accepts_matching_company_prefix(monkeypatch):
    project = _Project(project_id=202, company_id=10, code_sequence=1)
    fake_company_model = type(
        "FakeCompanyModel",
        (_FakeCompanyModel,),
        {"query": _CompanyQueryStub([_Company(company_id=10, client_code="M1", name="Empresa Laboratorio")])},
    )
    fake_project_model = type(
        "FakeProjectModel",
        (_FakeProjectModel,),
        {"query": _ProjectQueryStub(project)},
    )
    monkeypatch.setattr(project_task_module, "Company", fake_company_model)
    monkeypatch.setattr(project_task_module, "Project", fake_project_model)

    resolved, error = ProjectTaskService.resolve_project_by_code(
        "M1.J.1",
        allowed_company_ids=[10],
    )

    assert error is None
    assert resolved is project
