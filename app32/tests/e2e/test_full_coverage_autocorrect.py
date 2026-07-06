from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = ROOT_DIR / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from app32.tests.e2e.core.full_coverage_autocorrect import build_full_coverage_audit, write_full_coverage_audit_report
from app32.tests.e2e.scripts.run_devfull_full_app_suite import FULL_APP_SUITE_IDS
from app32.tests.e2e.scripts.run_full_system_suite import FULL_APP_DEPENDENCIES
from services.robot_tests_center_service import RobotTestsCenterService


def test_full_coverage_autocorrect_builds_coverage_matrix_for_m1():
    report = build_full_coverage_audit(company_id=10, run_id="run_test")

    assert report["company_id"] == 10
    assert report["environment"] == "DEV_FULL"
    assert report["coverage_matrix"]["app_routes_total"] > 0
    assert report["coverage_matrix"]["ui_screens_total"] > 0
    assert report["coverage_matrix"]["ui_fields_total"] >= 0
    assert report["coverage_matrix"]["mcp_tools_total"] >= 0
    assert report["coverage_matrix"]["ui_elements_in_inactive_templates_total"] >= 0
    assert report["coverage_matrix"]["app_routes_auto_contract_generated_total"] >= 0
    assert report["coverage_matrix"]["api_get_routes_auto_contract_generated_total"] >= 0
    assert report["coverage_matrix"]["get_report_download_contract_generated_total"] >= 0
    assert report["coverage_matrix"]["ai_validation_guard_contract_generated_total"] >= 0
    assert report["coverage_matrix"]["consultive_tenant_contract_covered_total"] >= 0
    assert report["coverage_matrix"]["real_estate_tenant_contract_covered_total"] >= 0
    assert report["coverage_matrix"]["contracts_tenant_contract_covered_total"] >= 0
    assert report["coverage_matrix"]["workspace_tenant_contract_covered_total"] >= 0
    assert report["coverage_matrix"]["route_mutation_existing_adapter_covered_total"] >= 0
    assert report["coverage_matrix"]["ui_human_gate_existing_adapter_covered_total"] >= 0
    assert report["coverage_matrix"]["ui_screens_auto_contract_generated_total"] >= 0
    assert report["coverage_matrix"]["coverage_gaps_total"] == 0
    assert report["coverage_matrix"]["execution_backlog_total"] >= 0
    assert report["coverage_matrix"]["classified_policy_covered_total"] >= 0
    assert "correction_candidates" in report
    assert "correction_groups" in report
    assert isinstance(report["correction_groups"], list)
    assert report["autocorrection"]["safe_automatic_actions"]


def test_full_coverage_autocorrect_writes_summary_manifest_and_artifact(tmp_path: Path):
    summary_path = write_full_coverage_audit_report(tmp_path, company_id=10, sync_aa_j1=False)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads((summary_path.parent / "manifest.json").read_text(encoding="utf-8"))

    assert summary["company_id"] == 10
    assert summary["suite_catalog_total"] > 0
    assert summary["aa_j_1_cards_total"] == 0
    assert summary["automatic_items_covered_total"] >= 0
    assert summary["coverage_gaps_total"] == 0
    assert summary["execution_backlog_total"] == summary["autocorrection_backlog_items_total"]
    autocorrection_log_path = Path(summary["autocorrection_log_path"])
    assert autocorrection_log_path.exists()
    log = json.loads(autocorrection_log_path.read_text(encoding="utf-8"))
    assert any(action["action_id"] == "ui_human_gate_existing_adapters_covered" for action in log["actions"])
    assert any(action["action_id"] == "ai_validation_guard_contracts_generated" for action in log["actions"])
    assert any(action["action_id"] == "consultive_tenant_contracts_covered" for action in log["actions"])
    assert any(action["action_id"] == "real_estate_tenant_contracts_covered" for action in log["actions"])
    assert any(action["action_id"] == "contracts_tenant_contracts_covered" for action in log["actions"])
    assert any(action["action_id"] == "workspace_tenant_contracts_covered" for action in log["actions"])
    assert manifest["suite_id"] == "full_coverage_autocorrect_audit"
    assert manifest["journeys"][0]["company_id"] == 10
    assert manifest["artifacts"][0]["kind"] == "full_coverage_audit"
    assert any(item["kind"] == "autocorrection_log" for item in manifest["artifacts"])


def test_robot_tests_center_exposes_full_coverage_autocorrect_package():
    packages = {item["key"]: item for item in RobotTestsCenterService.list_execution_packages(e2e_state={})}

    package = packages["coverage_audit"]
    assert package["suite_id"] == "full_coverage_autocorrect_audit"
    assert package["forced_environment"] == "DEV_FULL"
    assert package["highlight"] is True


def test_robot_tests_center_uses_configured_robot_user_for_devfull_global_packages(monkeypatch):
    monkeypatch.setenv("APP32_E2E_DEV_USER_ID", "19")

    assert RobotTestsCenterService._resolve_dev_full_robot_user_id(
        environment="DEV_FULL",
        suite_id="full_system_validation",
        fallback_user_id=16,
    ) == 19
    assert RobotTestsCenterService._resolve_dev_full_robot_user_id(
        environment="PROD_SAFE",
        suite_id="full_system_validation",
        fallback_user_id=16,
    ) == 16
    assert RobotTestsCenterService._resolve_dev_full_robot_user_id(
        environment="DEV_FULL",
        suite_id="reports_functional_probe",
        fallback_user_id=16,
    ) == 16


def test_robot_tests_center_start_run_routes_coverage_button_to_robot_user(monkeypatch):
    captured = {}

    def fake_start_execution(**kwargs):
        captured.update(kwargs)
        return {"execution_id": "exec-test", "status": "running"}

    monkeypatch.setenv("APP32_E2E_DEV_USER_ID", "19")
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2ESupervisedExecutionService.start_execution",
        fake_start_execution,
    )

    result = RobotTestsCenterService.start_run(
        package_key="coverage_audit",
        suite_id=None,
        environment="PROD_SAFE",
        company_id=10,
        user_id=16,
    )

    assert result["suite_id"] == "full_coverage_autocorrect_audit"
    assert result["environment"] == "DEV_FULL"
    assert captured["company_id"] == 10
    assert captured["user_id"] == 19


def test_full_coverage_autocorrect_is_part_of_full_app_aggregates():
    assert "full_coverage_autocorrect_audit" in FULL_APP_DEPENDENCIES
    assert "full_coverage_autocorrect_audit" in FULL_APP_SUITE_IDS


def test_full_coverage_autocorrect_maps_generic_api_routes_to_existing_adapter_domains():
    from app32.tests.e2e.core.full_coverage_autocorrect import _route_module

    assert _route_module("/api/ai-monitoring/requests") == "admin"
    assert _route_module("/api/cadastro-agent/empresa/iniciar") == "admin"
    assert _route_module("/api/activity-work-logs/<log_id>") == "processes"
    assert _route_module("/agents/cadastro") == "admin"
    assert _route_module("/api/incentives/calculate") == "financial"
    assert _route_module("/api/indicator-data") == "processes"
    assert _route_module("/api/usuarios") == "admin"
    assert _route_module("/api/consultive/business-reviews") == "consultive"
    assert _route_module("/api/real-estate-auctions/properties") == "real_estate"
    assert _route_module("/api/ai/board/start") == "ai"
    assert _route_module("/api/v2/chat") == "ai"
    assert _route_module("/main") == "workspace"


def test_full_coverage_autocorrect_ai_routes_are_guard_contractable():
    from app32.tests.e2e.core.full_coverage_autocorrect import _is_ai_validation_guard_contractable

    assert _is_ai_validation_guard_contractable("/api/ai/board/start", {"POST"}) is True
    assert _is_ai_validation_guard_contractable("/api/ai/board/resume", {"POST"}) is True
    assert _is_ai_validation_guard_contractable("/api/v2/chat", {"POST"}) is True
    assert _is_ai_validation_guard_contractable("/api/consultive/protocols", {"POST"}) is False


def test_full_coverage_autocorrect_consultive_routes_are_tenant_contract_covered():
    from app32.tests.e2e.core.full_coverage_autocorrect import _is_consultive_tenant_contract_covered

    suites = {"consultive_tenant_contract_probe"}
    assert _is_consultive_tenant_contract_covered("/api/consultive/business-reviews", {"GET", "POST"}, suites) is True
    assert _is_consultive_tenant_contract_covered("/api/consultive/urgent-needs/<urgent_need_id>/status", {"POST"}, suites) is True
    assert _is_consultive_tenant_contract_covered("/api/real-estate-auctions/properties", {"GET", "POST"}, suites) is False


def test_full_coverage_autocorrect_real_estate_routes_are_tenant_contract_covered():
    from app32.tests.e2e.core.full_coverage_autocorrect import _is_real_estate_tenant_contract_covered

    suites = {"real_estate_tenant_contract_probe"}
    assert _is_real_estate_tenant_contract_covered("/api/real-estate-auctions/properties", {"GET", "POST"}, suites) is True
    assert _is_real_estate_tenant_contract_covered("/api/real-estate-auctions/properties/<property_id>/events/<event_id>", {"PATCH", "DELETE"}, suites) is True
    assert _is_real_estate_tenant_contract_covered("/api/consultive/business-reviews", {"GET", "POST"}, suites) is False


def test_full_coverage_autocorrect_contracts_and_workspace_are_tenant_contract_covered():
    from app32.tests.e2e.core.full_coverage_autocorrect import (
        _is_contracts_tenant_contract_covered,
        _is_workspace_tenant_contract_covered,
    )

    assert _is_contracts_tenant_contract_covered(
        "/contracts/catalogs/items",
        {"GET", "POST"},
        {"contracts_tenant_contract_probe"},
    ) is True
    assert _is_contracts_tenant_contract_covered(
        "/contracts/list",
        {"GET", "POST"},
        {"contracts_tenant_contract_probe"},
    ) is True
    assert _is_workspace_tenant_contract_covered("/main", {"GET"}, {"workspace_tenant_contract_probe"}) is True
    assert _is_workspace_tenant_contract_covered("/contracts/list", {"GET"}, {"workspace_tenant_contract_probe"}) is False
