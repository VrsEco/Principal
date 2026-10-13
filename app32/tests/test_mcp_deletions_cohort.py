"""Exclusões de projeto, atividade e reunião pelo conector comum: confirmação oculta, aprovação obrigatória e pré-validação."""

import inspect
from types import SimpleNamespace

import pytest

from src.core import mcp_prevalidation as pre
from src.core.mcp_gate_policy import requires_persisted_approval
from src.core.mcp_mutation_contract import CONFIRM_PARAM
from src.core.mcp_param_hiding import HIDDEN_CLIENT_PARAMETERS, adapt_for_mcp, description_for_mcp
from src.core.mcp_write_cohorts import WRITE_COHORT_TOOL_NAMES

DELETIONS = ("delete_project", "delete_project_task_secure", "restore_project_task_secure", "delete_meeting_secure")


def test_the_deletions_cohort_is_exactly_these_four_tools():
    assert tuple(WRITE_COHORT_TOOL_NAMES["deletions"]) == DELETIONS


# ---- a confirmação não é do cliente ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", DELETIONS)
def test_confirm_is_hidden_from_the_client_and_injected_for_the_shared_tool(name):
    seen = {}

    def tool(task_id: int = 0, reason: str = "x", confirm: bool = False, company_id: int = None):
        seen.update(confirm=confirm, task_id=task_id)
        return {"success": True}

    tool.__name__ = name
    adapted = adapt_for_mcp(name, tool)
    assert "confirm" not in inspect.signature(adapted).parameters
    adapted(task_id=7, reason="teste", confirm=False)  # mesmo que o cliente tentasse enviar False
    assert seen["confirm"] is True and seen["task_id"] == 7


def test_confirm_text_is_removed_from_the_published_descriptions():
    description = "Exclui.\n:param reason: Motivo.\n:param confirm: Deve ser True para confirmar.\n:param company_id: Empresa."
    cleaned = description_for_mcp("delete_meeting_secure", description)
    assert ":param confirm:" not in cleaned and ":param reason:" in cleaned


@pytest.mark.parametrize("name", DELETIONS)
def test_every_deletion_requires_the_persisted_human_approval(name):
    from src.intelligence.tool_catalog import catalog

    assert requires_persisted_approval(name, catalog.get_tool_capability(name)) is True


def test_guard_any_tool_with_a_hidden_confirmation_must_require_persisted_approval():
    """Injetar confirm=True só é seguro porque o runtime já exige aprovação persistida para a ferramenta."""
    from src.intelligence.tool_catalog import catalog

    offenders = []
    for name, hidden in HIDDEN_CLIENT_PARAMETERS.items():
        injects_confirmation = any(CONFIRM_PARAM.match(param) and value is True for param, value in hidden.items())
        if injects_confirmation and not requires_persisted_approval(name, catalog.get_tool_capability(name)):
            offenders.append(name)
    assert not offenders, f"confirmação injetada sem aprovação persistida: {offenders}"


@pytest.mark.parametrize("name", DELETIONS)
def test_each_deletion_is_reachable_by_the_common_connector_and_keeps_the_admin_surface(name):
    from src.intelligence.tool_catalog import catalog
    from src.intelligence.tooling.capabilities import ToolScope

    capability = catalog.get_tool_capability(name)
    scopes = {getattr(scope, "value", scope) for scope in capability.scopes}
    assert {ToolScope.MCP_USER.value, ToolScope.MCP_ADMIN.value} <= scopes
    assert capability.human_gate is True and capability.permissions


# ---- pré-validação: o alvo existe e está no estado certo ----------------------------------------------------------
def _patch_project(monkeypatch, project, error=None):
    from services.project_mcp_service import ProjectMCPService

    seen = {}
    monkeypatch.setattr(
        ProjectMCPService, "get_project", staticmethod(lambda **k: seen.update(k) or (project, error))
    )
    return seen


def test_project_delete_prevalidation(monkeypatch):
    seen = _patch_project(monkeypatch, None, "Projeto não encontrado no tenant informado.")
    assert pre.project_delete({"company_id": 10, "project_id": 99}).startswith("Projeto não encontrado")
    assert seen["include_deleted"] is True and seen["company_id"] == 10
    _patch_project(monkeypatch, SimpleNamespace(is_deleted=True))
    assert pre.project_delete({"company_id": 10, "project_code": "M1.J.9"}) == "Projeto já está removido logicamente."
    _patch_project(monkeypatch, SimpleNamespace(is_deleted=False))
    assert pre.project_delete({"company_id": 10, "project_id": 69}) is None
    assert pre.project_delete({"project_id": 69}) is None, "sem empresa, o runtime decide"


def _patch_task(monkeypatch, task, error=None):
    from services.project_task_mcp_service import ProjectTaskMCPService

    monkeypatch.setattr(ProjectTaskMCPService, "get_task", staticmethod(lambda **k: (task, error)))


def test_task_delete_and_restore_prevalidation(monkeypatch):
    _patch_task(monkeypatch, None, "Atividade de projeto não encontrada no tenant informado.")
    assert pre.task_delete({"company_id": 9, "task_id": 1}).startswith("Atividade de projeto não encontrada")
    assert pre.task_restore({"company_id": 9, "task_id": 1}).startswith("Atividade de projeto não encontrada")
    _patch_task(monkeypatch, SimpleNamespace(is_deleted=True))
    assert pre.task_delete({"company_id": 9, "task_id": 1}) == "Atividade já está removida logicamente."
    assert pre.task_restore({"company_id": 9, "task_id": 1}) is None
    _patch_task(monkeypatch, SimpleNamespace(is_deleted=False))
    assert pre.task_delete({"company_id": 9, "task_id": 1}) is None
    assert pre.task_restore({"company_id": 9, "task_id": 1}) == "Atividade não está soft-deletada."


def test_meeting_delete_prevalidation(monkeypatch):
    import models.meeting as meeting_module

    class _Query:
        def __init__(self, row):
            self.row = row

        def filter_by(self, **kwargs):
            self.kwargs = kwargs
            return self

        def first(self):
            return self.row

    monkeypatch.setattr(meeting_module, "Meeting", SimpleNamespace(query=_Query(None)))
    assert pre.meeting_delete({"company_id": 10, "meeting_id": 114}) == "Reunião ID 114 não encontrada na empresa selecionada."
    assert pre.meeting_delete({"company_id": 10, "meeting_id": "x"}) == "meeting_id inválido."
    monkeypatch.setattr(meeting_module, "Meeting", SimpleNamespace(query=_Query(SimpleNamespace(id=114))))
    assert pre.meeting_delete({"company_id": 10, "meeting_id": 114}) is None


def test_every_deletion_has_a_prevalidator():
    assert set(DELETIONS) <= set(pre.PREVALIDATORS)
