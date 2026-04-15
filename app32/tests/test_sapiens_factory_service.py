import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.external_llm_factory_service import ExternalLLMFactoryService
from services.sapiens_factory_service import SapiensFactoryService


def test_assess_change_request_infers_financial_full_stack():
    result = SapiensFactoryService.assess_change_request(
        {
            "request_text": "Precisamos criar uma nova função completa para consultar os resultados financeiros da empresa.",
            "execution_mode": "plan",
        },
        actor_context={"user_id": 7, "role": "admin", "company_id": 31, "accessible_company_ids": [31]},
    )

    assert result["request"]["change_type"] == "create"
    assert result["request"]["domain"] == "finance"
    assert result["request"]["target_object"] == "capability:financial_results_query"
    assert result["risk_level"] == "high"
    assert result["human_gate_required"] is True
    assert "service_spec" in result["recommended_artifacts"]


def test_assess_change_request_infers_tool_fix():
    result = SapiensFactoryService.assess_change_request(
        {
            "request_text": "Precisamos dar manutenção na tool xyz pois está dando erro.",
            "execution_mode": "diagnose",
        }
    )

    assert result["request"]["change_type"] == "fix"
    assert "tool_contract" in result["request"]["target_layers"]
    assert result["request"]["target_object"] == "tool:xyz"
    assert result["risk_level"] in {"medium", "high"}


def test_external_llm_surface_manifest_is_split_ready():
    manifest = ExternalLLMFactoryService.build_surface_manifest()

    assert manifest["current_strategy"]["mode"] == "single_surface_now_split_ready"
    assert "financeiro" in manifest["future_scope"]
