from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.interaction_service import KnowledgeInteractionService
from services.knowledge.query_service import KnowledgeTenantContextError


class QueryServiceSpy:
    def __init__(self):
        self.calls = []

    def answer(self, question, **kwargs):
        self.calls.append((question, kwargs))
        return {
            "answer": "Resposta",
            "citations": [{"id": "citation-1"}],
            "warnings": [],
            "trust_signals": ["official"],
            "actions": [],
        }


def test_product_scope_never_receives_tenant_artificially():
    spy = QueryServiceSpy()
    payload = KnowledgeInteractionService(spy).answer(
        "Como publicar um processo?",
        scope="product",
        company_id=91,
        user_id=7,
    )

    _, kwargs = spy.calls[0]
    assert kwargs["company_id"] is None
    assert kwargs["require_company"] is False
    assert kwargs["source_types"] == ("product_help", "system_documentation")
    assert payload["presentation"]["source_label"] == "Manual oficial"
    assert payload["interaction_id"]
    assert payload["understanding"]["intent"] == "product_help"
    assert payload["understanding"]["domain"] in {"app_versus_usage", "processes"}


def test_company_scope_is_tenant_bound_and_excludes_product():
    spy = QueryServiceSpy()
    KnowledgeInteractionService(spy).answer(
        "Qual foi a decisão?",
        scope="company",
        company_id=44,
        user_id=7,
        employee_id=8,
    )

    _, kwargs = spy.calls[0]
    assert kwargs["company_id"] == 44
    assert kwargs["include_product"] is False
    assert kwargs["user_id"] == 7
    assert kwargs["employee_id"] == 8


def test_financial_how_to_question_is_understood_as_product_help():
    understanding = KnowledgeInteractionService(QueryServiceSpy()).understand_question(
        "Como eu faço para ver os títulos financeiros em aberto?",
        requested_scope="all",
    )

    assert understanding["intent"] == "product_help"
    assert understanding["domain"] == "finance"
    assert "how_to_question" in understanding["signals"]
    assert "finance_terms" in understanding["signals"]


def test_how_to_create_question_does_not_turn_into_operational_action():
    understanding = KnowledgeInteractionService(QueryServiceSpy()).understand_question(
        "Como criar um processo no portal?",
        requested_scope="all",
    )

    assert understanding["intent"] == "product_help"
    assert understanding["domain"] == "processes"
    assert understanding["clarification_required"] is False


def test_company_scope_fails_closed_without_active_company():
    with pytest.raises(KnowledgeTenantContextError):
        KnowledgeInteractionService(QueryServiceSpy()).answer(
            "Qual foi a decisão?",
            scope="company",
            company_id=None,
            user_id=7,
        )
