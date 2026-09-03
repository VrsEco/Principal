from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge.adapters.product_help import ProductHelpKnowledgeAdapter
from services.knowledge.interaction_service import KnowledgeInteractionService


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_SET_PATH = ROOT / "knowledge" / "golden_sets" / "sapiens_fase1_product_help_pt_br.json"
FORBIDDEN_USER_TERMS = ("MCP", "API", "endpoint", "contrato financeiro", "get_", "paper", "spec")


class QueryServiceSpy:
    def __init__(self):
        self.calls = []

    def answer(self, question, **kwargs):
        self.calls.append((question, kwargs))
        return {
            "answer": "Resposta fallback",
            "citations": [],
            "warnings": ["fallback_called"],
            "trust_signals": [],
            "actions": [],
        }


def _golden_set() -> dict:
    return json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))


def test_sapiens_fase1_golden_set_is_versioned_and_user_safe():
    payload = _golden_set()

    assert payload["golden_set_id"] == "sapiens_fase1_product_help_pt_br"
    assert payload["version"] == "2026-09-03"
    assert len(payload["cases"]) >= 5
    assert payload["rules"]["tenant_policy"].startswith("company_id sempre vem da sessão")
    for case in payload["cases"]:
        assert case["id"]
        assert case["question"]
        assert case["expected_intent"] == "product_help"
        assert case["expected_domain"] in {"routine", "finance", "processes"}
        assert case["expected_actions"]


def test_product_help_catalog_covers_every_fase1_golden_source_ref():
    documents = ProductHelpKnowledgeAdapter(ROOT / "knowledge" / "product_help").discover_documents()
    source_refs = {document.source_ref for document in documents}

    expected = {
        ref
        for case in _golden_set()["cases"]
        for ref in case.get("expected_source_refs", [])
    }

    assert expected <= source_refs


def test_fase1_golden_questions_have_deterministic_user_friendly_answers():
    service = KnowledgeInteractionService(QueryServiceSpy())

    for case in _golden_set()["cases"]:
        payload = service.answer(
            case["question"],
            scope=case["scope"],
            company_id=44,
            user_id=7,
        )
        action_targets = [action["target"] for action in payload["actions"]]
        answer = payload["answer"]

        assert payload["understanding"]["intent"] == case["expected_intent"]
        assert payload["understanding"]["domain"] == case["expected_domain"]
        assert payload["query_plan"]["query_kind"] == "direct_product_help"
        assert not payload["warnings"]
        for target in case["expected_actions"]:
            assert target in action_targets
        for term in case["must_include"]:
            assert term in answer
        assert not any(term in answer for term in FORBIDDEN_USER_TERMS)
