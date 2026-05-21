import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.process_pop_copilot_service import suggest_process_pop_step_description
from src.intelligence import llm as llm_module


def test_suggest_process_pop_step_description_falls_back_to_heuristic(monkeypatch):
    context = {
        "step": {
            "id": 5,
            "routine_id": 9,
            "name": "Importar extrato",
            "expected_result": "o extrato fica importado",
            "video_narration": "Entrar no menu conciliação, escolher a conta e confirmar a importação.",
        },
        "routine": {
            "id": 9,
            "process_id": 12,
            "name": "Conciliação bancária",
        },
        "coverage": {
            "has_video": True,
            "has_image": False,
            "has_description": False,
        },
    }

    monkeypatch.setattr('services.process_pop_copilot_service.build_process_pop_step_media_context', lambda **kwargs: context)

    class _BrokenLLM:
        def with_structured_output(self, *_args, **_kwargs):
            raise RuntimeError("llm offline")

    monkeypatch.setattr(llm_module, 'llm_expert', _BrokenLLM())

    payload = suggest_process_pop_step_description(company_id=9, step_id=5)

    assert payload["draft"]["source"] == "heuristic"
    assert "Importar extrato" in payload["draft"]["suggested_description"]
    assert "o extrato fica importado" in payload["draft"]["suggested_expected_result"]
