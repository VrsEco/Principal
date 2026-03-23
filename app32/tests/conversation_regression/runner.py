import json
import os
from typing import Any, Dict, List

from src.intelligence import menu_engine

from .helpers import build_option, discover_action, run_whatsapp_turns


FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cases.json")


def load_catalog() -> Dict[str, List[Dict[str, Any]]]:
    with open(FIXTURES_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_chapter_cases(chapter_key: str) -> List[Dict[str, Any]]:
    return list(load_catalog().get(chapter_key, []))


def case_ids(chapter_key: str) -> List[str]:
    return [case["id"] for case in load_chapter_cases(chapter_key)]


def build_options(option_specs: List[Dict[str, Any]]):
    return [build_option(**spec) for spec in option_specs]


def _project_task_create_executor(option, payload, company_id, user_id, channel="web"):
    if payload.get("codigo_projeto") and payload.get("nome_atividade"):
        return f"atividade criada: {payload['codigo_projeto']} - {payload['nome_atividade']}"
    return None


EXECUTOR_REGISTRY = {
    "project_task_create": _project_task_create_executor,
}


def execute_case(monkeypatch, case: Dict[str, Any]) -> None:
    case_type = case["type"]
    if case_type == "parsing":
        payload = menu_engine._extract_fields_from_text(case["input"])
        for key, expected_value in case.get("expected_payload", {}).items():
            assert payload.get(key) == expected_value
        for absent_key in case.get("expected_absent_keys", []):
            assert absent_key not in payload
        return

    if case_type == "routing":
        options = build_options(case["options"])
        action_key, telemetry = discover_action(case["input"], options)
        assert action_key == case["expected_action_key"]
        assert telemetry["selected_action_key"] == case["expected_action_key"]
        return

    if case_type == "multiturn":
        option = build_option(**case["option"])
        session, results = run_whatsapp_turns(
            monkeypatch=monkeypatch,
            option=option,
            turns=case["turns"],
            direct_executor=EXECUTOR_REGISTRY[case["direct_executor"]],
            selection_payload=case.get("selection_payload"),
            company_choices=case.get("company_choices"),
        )
        for index, expected_text in enumerate(case.get("expected_turn_contains", [])):
            assert expected_text in results[index].response_text
        assert results[-1].response_text == case["expected_final_response"]
        assert session.status == case.get("expected_session_status", "idle")
        return

    raise AssertionError(f"Tipo de caso conversacional não suportado: {case_type}")
