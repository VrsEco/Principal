import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_execution_contract_service import (
    apply_contract_defaults,
    normalize_execution_mode,
)


def test_normalize_execution_mode_supports_manual_external():
    assert normalize_execution_mode("manual_external") == "manual_external"
    assert normalize_execution_mode(None) == "manual_external"
    assert normalize_execution_mode("ai_task") == "ai_task"
    assert normalize_execution_mode("ai_decision") == "ai_decision"
    assert normalize_execution_mode("external_rest") == "api_task"
    assert normalize_execution_mode("external_mcp") == "mcp_task"
    assert normalize_execution_mode("open_form") == "open_form"


def test_normalize_execution_mode_rejects_invalid_mode():
    with pytest.raises(ValueError):
        normalize_execution_mode("email_bot")


def test_apply_contract_defaults_enriches_payload():
    payload = {"bpmn_element_id": "Activity_External"}
    contract = SimpleNamespace(
        id=77,
        execution_mode="ai_task",
        interaction_mode="drawer",
        capability_key="contract.review",
        auto_service_key="process.dispatch",
        route_name="contract.review",
        requires_human_gate=True,
        allows_pause=False,
        allows_retry=True,
        sla_minutes=90,
        ui_schema_json={"tab": "review"},
        rest_config_json={"url": "https://api.example.test"},
        mcp_config_json={},
        ai_config_json={"instruction": "Leia o documento.", "allowed_tools": ["documents.read"]},
        completion_rules_json={"success_http_status": [200, 202]},
    )

    enriched = apply_contract_defaults(payload, contract)

    assert enriched["execution_mode"] == "ai_task"
    assert enriched["interaction_mode"] == "drawer"
    assert enriched["capability_key"] == "contract.review"
    assert enriched["handler_key"] == "process.dispatch"
    assert enriched["metadata_json"]["contract_id"] == 77
    assert enriched["metadata_json"]["requires_human_gate"] is True
    assert enriched["ai_config_json"]["instruction"] == "Leia o documento."
