import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_ai_execution_service import normalize_ai_contract_config


def test_normalize_ai_task_contract_config():
    config = normalize_ai_contract_config(
        {
            "instruction": "Leia o documento e extraia valor e data.",
            "allowed_tools": ["documents.read", "documents.read"],
            "tool_source": "mcp",
            "output_schema": {"type": "object"},
            "temperature": 0.1,
            "min_confidence": 0.9,
        },
        execution_mode="ai_task",
    )

    assert config["instruction"] == "Leia o documento e extraia valor e data."
    assert config["allowed_tools"] == ["documents.read"]
    assert config["tool_source"] == "mcp"
    assert config["min_confidence"] == 0.9
    assert config["output_schema"] == {"type": "object"}


def test_normalize_ai_decision_requires_allowed_decisions():
    with pytest.raises(ValueError):
        normalize_ai_contract_config(
            {"instruction": "Escolha a melhor rota."},
            execution_mode="ai_decision",
        )


def test_normalize_ai_decision_accepts_closed_options():
    config = normalize_ai_contract_config(
        {
            "instruction": "Escolha entre archive ou finance.",
            "allowed_decisions": ["archive", "finance"],
            "tool_source": "none",
        },
        execution_mode="ai_decision",
    )

    assert config["allowed_decisions"] == ["archive", "finance"]
    assert config["fallback_action"] == "human_review"
