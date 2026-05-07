import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_execution_mode_service import (
    get_execution_mode_catalog,
    normalize_contract_configs,
    normalize_execution_mode,
)


def test_execution_mode_catalog_exposes_new_modes():
    catalog = get_execution_mode_catalog()

    task_modes = {item["key"] for item in catalog["task_modes"]}
    assert {"open_form", "open_app32_page", "api_task", "mcp_task", "ai_task"}.issubset(task_modes)


def test_normalize_contract_configs_for_open_form():
    payload = normalize_contract_configs(
        {
            "execution_mode": "open_form",
            "ui_schema_json": {
                "form_code": "financial_review",
                "prefill_mapping": {"document_id": "{{process.document_id}}"},
            },
        }
    )

    assert payload["execution_mode"] == "open_form"
    assert payload["interaction_mode"] == "drawer"
    assert payload["ui_schema_json"]["form_code"] == "financial_review"
    assert payload["auto_service_key"] == "process.open_form"


def test_normalize_contract_configs_for_api_task_requires_connection():
    with pytest.raises(ValueError):
        normalize_contract_configs(
            {
                "execution_mode": "api_task",
                "rest_config_json": {"method": "POST", "path": "/x"},
            }
        )


def test_normalize_execution_mode_aliases_legacy_rest_and_mcp():
    assert normalize_execution_mode("external_rest") == "api_task"
    assert normalize_execution_mode("external_mcp") == "mcp_task"
