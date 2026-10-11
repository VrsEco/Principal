"""Backlog de sugestões e pedidos de integração: projeto operacional VIGENTE, não códigos fixos/históricos."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import services.engineering_backlog_project_service as resolver
from services.engineering_suggestion_request_service import EngineeringSuggestionRequestService
from services.integration_request_service import IntegrationRequestService


def test_resolver_returns_the_marked_project_code(monkeypatch):
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: SimpleNamespace(code="AA.J.21"))
    assert resolver.current_engineering_project_code("AA.J.1") == "AA.J.21"


def test_resolver_falls_back_when_no_project_is_marked(monkeypatch):
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: None)
    assert resolver.current_engineering_project_code("AA.J.1") == "AA.J.1"


def test_resolver_falls_back_when_the_lookup_fails(monkeypatch):
    def boom():
        raise RuntimeError("Working outside of application context")

    monkeypatch.setattr(resolver, "_find_marked_project", boom)
    assert resolver.current_engineering_project_code("AA.J.31") == "AA.J.31"


def test_marker_and_company_follow_the_documented_convention():
    assert resolver.OPERATIONAL_MARKER == "ENGINEERING_OPERATIONAL_CURRENT=1"
    assert resolver.ENGINEERING_COMPANY_CODE == "AA"


# ---- sugestões de engenharia ------------------------------------------------------------------
def test_engineering_suggestions_go_to_the_current_project(monkeypatch):
    monkeypatch.delenv("ENGINEERING_REQUEST_PROJECT_CODE", raising=False)
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: SimpleNamespace(code="AA.J.21"))
    assert EngineeringSuggestionRequestService.backlog_project_code() == "AA.J.21"


def test_an_explicit_env_override_wins(monkeypatch):
    monkeypatch.setenv("ENGINEERING_REQUEST_PROJECT_CODE", "AA.J.99")
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: SimpleNamespace(code="AA.J.21"))
    # BACKLOG_PROJECT_CODE é lido do ambiente na importação; aqui só importa que a env desliga a resolução.
    assert EngineeringSuggestionRequestService.backlog_project_code() == EngineeringSuggestionRequestService.BACKLOG_PROJECT_CODE


def test_old_cards_in_the_legacy_project_are_still_listed(monkeypatch):
    """Ao mudar para o projeto vigente, os cards já criados em AA.J.1 não podem sumir de 'minhas sugestões'."""
    monkeypatch.delenv("ENGINEERING_REQUEST_PROJECT_CODE", raising=False)
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: SimpleNamespace(code="AA.J.21"))
    ids = {"AA.J.21": 171, "AA.J.1": 31}
    monkeypatch.setattr(
        "services.engineering_suggestion_request_service.ProjectTaskService.resolve_project_by_code",
        lambda code, allowed_company_ids=None: (SimpleNamespace(id=ids[code]), None),
    )
    assert EngineeringSuggestionRequestService._project_id() == 171
    assert EngineeringSuggestionRequestService._legacy_project_id() == 31


def test_no_legacy_lookup_when_the_current_project_is_the_legacy_one(monkeypatch):
    monkeypatch.delenv("ENGINEERING_REQUEST_PROJECT_CODE", raising=False)
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: None)
    assert EngineeringSuggestionRequestService._legacy_project_id() is None


# ---- pedidos de integração --------------------------------------------------------------------
def test_integration_requests_go_to_the_current_project(monkeypatch):
    monkeypatch.delenv("INTEGRATION_REQUEST_PROJECT_CODE", raising=False)
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: SimpleNamespace(code="AA.J.21"))
    assert IntegrationRequestService.backlog_project_code() == "AA.J.21"


def test_integration_requests_keep_the_old_code_only_as_the_last_resort(monkeypatch):
    monkeypatch.delenv("INTEGRATION_REQUEST_PROJECT_CODE", raising=False)
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: None)
    assert IntegrationRequestService.backlog_project_code() == "AA.J.31"


def test_integration_request_creates_its_card_in_the_resolved_project(monkeypatch):
    monkeypatch.delenv("INTEGRATION_REQUEST_PROJECT_CODE", raising=False)
    monkeypatch.setattr(resolver, "_find_marked_project", lambda: SimpleNamespace(code="AA.J.21"))
    added, seen = [], {}
    session = SimpleNamespace(add=added.append, flush=lambda: setattr(added[-1], "id", 5), commit=lambda: None)
    monkeypatch.setattr("services.integration_request_service.db", SimpleNamespace(session=session))
    monkeypatch.setattr(
        "services.integration_request_service.ProjectTaskService.create_project_task",
        lambda **kw: (seen.update(kw) or {"task": SimpleNamespace(id=900)}, None),
    )
    record = IntegrationRequestService.create_request(
        {
            "title": "Open Finance Banco X", "business_domain": "Financeiro", "integration_mode": "consume",
            "technical_channel": "api_mcp", "external_system": "Banco X",
            "objective": "Consumir extratos bancários para conciliação.", "data_summary": "Extratos e saldos bancários.",
        },
        company_id=9, requester_user_id=3,
    )
    assert seen["project_code"] == "AA.J.21" and record.backlog_task_id == 900
