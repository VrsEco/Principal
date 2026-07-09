import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.robot_tests_center_service import RobotTestsCenterService


def test_robot_tests_center_builds_functional_overview(monkeypatch):
    fake_e2e_state = {
        "suite_catalog": [
            {"suite_id": "full_system_validation", "label": "Teste completo", "domain": "system", "summary": "Completo."},
            {"suite_id": "financial_functional_probe", "label": "Financeiro", "domain": "financial", "summary": "Financeiro."},
            {"suite_id": "reports_functional_probe", "label": "Relatórios", "domain": "reports", "summary": "Relatórios."},
        ],
        "latest_runs": [
            {
                "run_id": "run-1",
                "generated_at": "2026-06-14T10:00:00",
                "status": "failed",
                "journeys_failed": 1,
                "journey_names": ["financial_functional_probe"],
                "failed_journey_names": ["financial_functional_probe"],
                "environment": "PROD_SAFE",
                "manifest_download_url": "/manifest",
            }
        ],
        "latest_diff": {"regressions": ["financial_functional_probe"], "recovered": [], "new_journeys": ["reports_functional_probe"]},
        "ui_inventory": {
            "generated_at": "2026-06-14T09:55:00",
            "screens_total": 321,
            "fields_total": 2952,
            "buttons_total": 2126,
            "links_total": 410,
            "coverage_gaps_total": 0,
            "automatic_items_covered_total": 3746,
        },
        "backlog_candidates": [
            {
                "title": "Falha E2E: financial_functional_probe",
                "failure_type": "assertion",
                "failed_step": "salvar",
                "run_id": "run-1",
                "company_id": 9,
                "environment": "PROD_SAFE",
                "manifest_download_url": "/manifest",
            }
        ],
        "devfull_transactional": {
            "run_id": "run-tx",
            "passed_suites": 6,
            "failed_suites": 0,
            "residue_total": 0,
            "controlled_mutation": {"mutating_steps_total": 20, "rollback_steps_total": 8},
        },
    }
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2EOperationsCenterService.build_frontend_state",
        lambda active_company: fake_e2e_state,
    )

    state = RobotTestsCenterService.build_overview_state(
        active_company=SimpleNamespace(id=9, name="M1 - Empresa de Testes Versus", client_code="M1"),
        company_id=9,
    )

    assert state["company"]["id"] == 9
    assert state["summary_cards"][2]["label"] == "Erros abertos"
    assert state["summary_cards"][2]["value"] == 1
    assert any(area["label"] == "Gestão Financeira" for area in state["areas"])
    assert state["errors"][0]["area_label"] == "Gestão Financeira"
    assert any(package["label"] == "Teste completo" for package in state["test_packages"])
    assert any(package["label"] == "Auditoria de cobertura total" for package in state["test_packages"])
    assert any(package["label"] == "Fazer teste completo DEV_FULL" for package in state["execution_packages"])
    assert any(package["label"] == "Atualizar inventário" for package in state["execution_packages"])
    assert any(package["label"] == "Cobrir tudo + AA.J.1" for package in state["execution_packages"])
    assert any(category["label"] == "Saúde do Sistema" for category in state["test_categories"])
    assert any(category["label"] == "Matriz de Cobertura Total" for category in state["test_categories"])
    assert any(category["label"] == "Cleanup / Reversão" for category in state["test_categories"])
    assert state["devfull_transactional"]["controlled_mutation"]["rollback_steps_total"] == 8
    assert state["history"][0]["run_id"] == "run-1"
    assert state["executive_summary"]["title"] == "Requer atenção"
    assert state["coverage_summary"]["screens_total"] == 321
    assert state["coverage_summary"]["coverage_gaps_total"] == 0
    assert state["history_diff"]["regressions_total"] == 1
    assert state["history_diff"]["new_journeys_total"] == 1
    assert state["errors"][0]["review_suite_id"] == "financial_functional_probe"
    assert state["errors"][0]["error_signature"]
    assert "Prompt pronto para o Squad de Engenharia" in state["errors"][0]["squad_prompt"]


def test_robot_tests_center_filters_errors_by_company(monkeypatch):
    fake_e2e_state = {
        "suite_catalog": [],
        "latest_runs": [],
        "backlog_candidates": [
            {"title": "Falha E2E: A", "failure_type": "timeout", "run_id": "run-a", "company_id": 9},
            {"title": "Falha E2E: B", "failure_type": "timeout", "run_id": "run-b", "company_id": 10},
        ],
    }

    errors = RobotTestsCenterService.list_open_errors(company_id=9, e2e_state=fake_e2e_state)

    assert len(errors) == 1
    assert errors[0]["run_id"] == "run-a"


def test_robot_tests_center_full_run_marks_only_failed_area_as_failed():
    fake_e2e_state = {
        "suite_catalog": [
            {"suite_id": "smoke_real_navigation", "label": "Smoke", "domain": "smoke", "summary": "Smoke."},
            {"suite_id": "financial_functional_probe", "label": "Financeiro", "domain": "financial", "summary": "Financeiro."},
            {"suite_id": "mcp_concurrency_probe", "label": "MCP", "domain": "mcp", "summary": "MCP."},
        ],
        "latest_runs": [
            {
                "run_id": "run-full",
                "generated_at": "2026-06-14T19:45:16",
                "status": "failed",
                "journeys_failed": 1,
                "journey_names": ["smoke::smoke_real_navigation", "financial::financial_functional_probe"],
                "failed_journey_names": ["smoke::smoke_real_navigation"],
                "environment": "PROD_SAFE",
            },
            {
                "run_id": "run-old",
                "generated_at": "2026-06-14T18:45:16",
                "status": "failed",
                "journeys_failed": 1,
                "journey_names": ["financial::financial_functional_probe"],
                "failed_journey_names": ["financial::financial_functional_probe"],
                "environment": "PROD_SAFE",
            }
        ],
    }

    areas = RobotTestsCenterService.list_area_latest(company_id=9, e2e_state=fake_e2e_state)
    by_id = {area["area_id"]: area for area in areas}

    assert by_id["smoke"]["status"] == "failed"
    assert by_id["financial"]["status"] == "passed"
    assert by_id["mcp"]["status"] == "observed"


def test_robot_tests_center_uses_clear_label_for_not_tested_cycle():
    area = RobotTestsCenterService._build_area_record(
        domain="financial",
        status="observed",
        latest=None,
        suite={"summary": "Financeiro."},
        company_id=9,
    )

    assert area["status_label"] == "Não testado neste ciclo"


def test_robot_tests_center_start_run_uses_supervised_e2e(monkeypatch):
    monkeypatch.setattr(
        RobotTestsCenterService,
        "_resolve_dev_full_robot_user_id",
        lambda **kwargs: kwargs.get("fallback_user_id"),
    )
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2ESupervisedExecutionService.start_execution",
        lambda suite_id, environment, **kwargs: {"execution_id": "exec-1", "suite_id": suite_id, "environment": environment},
    )

    result = RobotTestsCenterService.start_run(
        package_key="complete",
        suite_id=None,
        environment="PROD_SAFE",
        company_id=9,
    )

    assert result["suite_id"] == "full_system_validation"
    assert result["environment"] == "DEV_FULL"
    assert result["execution"]["execution_id"] == "exec-1"


def test_robot_tests_center_start_run_accepts_canonical_category(monkeypatch):
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2ESupervisedExecutionService.start_execution",
        lambda suite_id, environment, **kwargs: {"execution_id": "exec-cat", "suite_id": suite_id, "environment": environment},
    )

    result = RobotTestsCenterService.start_run(
        package_key="coverage_drift",
        suite_id=None,
        environment="PROD_SAFE",
        company_id=9,
    )

    assert result["suite_id"] == "drift_detection"
    assert result["execution"]["execution_id"] == "exec-cat"


def test_robot_tests_center_start_run_accepts_inventory_update(monkeypatch):
    monkeypatch.setattr(
        RobotTestsCenterService,
        "_resolve_dev_full_robot_user_id",
        lambda **kwargs: kwargs.get("fallback_user_id"),
    )
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2ESupervisedExecutionService.start_execution",
        lambda suite_id, environment, **kwargs: {"execution_id": "exec-coverage", "suite_id": suite_id, "environment": environment},
    )

    result = RobotTestsCenterService.start_run(
        package_key="inventory_update",
        suite_id=None,
        environment="PROD_SAFE",
        company_id=9,
    )

    assert result["suite_id"] == "ui_inventory_contract_scan"
    assert result["environment"] == "DEV_FULL"
    assert result["execution"]["execution_id"] == "exec-coverage"


def test_robot_tests_center_previous_failures_selects_focused_suite(monkeypatch):
    fake_e2e_state = {
        "suite_catalog": [],
        "latest_runs": [],
        "backlog_candidates": [
            {
                "title": "Falha E2E: financial_functional_probe",
                "failure_type": "assertion",
                "failed_step": "financial save",
                "run_id": "run-fin",
                "company_id": 9,
                "environment": "DEV_FULL",
            }
        ],
    }
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2EOperationsCenterService.build_frontend_state",
        lambda active_company: fake_e2e_state,
    )
    monkeypatch.setattr(
        RobotTestsCenterService,
        "_resolve_dev_full_robot_user_id",
        lambda **kwargs: kwargs.get("fallback_user_id"),
    )
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2ESupervisedExecutionService.start_execution",
        lambda suite_id, environment, **kwargs: {"execution_id": "exec-review", "suite_id": suite_id, "environment": environment},
    )

    result = RobotTestsCenterService.start_run(
        package_key="previous_failures",
        suite_id=None,
        environment="PROD_SAFE",
        company_id=9,
        user_id=7,
    )

    assert result["suite_id"] == "financial_functional_probe"
    assert result["environment"] == "DEV_FULL"
    assert result["review_scope"]["mode"] == "single_area"
    assert result["execution"]["execution_id"] == "exec-review"


def test_robot_tests_center_create_backlog_links_selected_error(monkeypatch):
    fake_e2e_state = {
        "suite_catalog": [],
        "latest_runs": [],
        "backlog_candidates": [
            {
                "title": "Falha E2E: financial_functional_probe",
                "failure_type": "assertion",
                "failed_step": "financial save",
                "run_id": "run-fin",
                "company_id": 9,
                "environment": "DEV_FULL",
                "manifest_download_url": "/manifest",
            }
        ],
    }
    monkeypatch.setattr(
        "services.robot_tests_center_service.E2EOperationsCenterService.build_frontend_state",
        lambda active_company: fake_e2e_state,
    )

    class Task:
        id = 456
        project_id = 144

        @property
        def code(self):
            return "AA.J.19.7"

    captured = {}

    def fake_create_task(**kwargs):
        captured.update(kwargs)
        return Task(), None

    result = RobotTestsCenterService.handle_error_action(
        error_id="run-fin-0",
        action="create_backlog",
        company_id=9,
        user_id=5,
        create_task_fn=fake_create_task,
    )

    assert result["created"][0]["task_code"] == "AA.J.19.7"
    assert result["created"][0]["task_url"] == "/projects/144/manage?task_id=456"
    assert captured["metadata"]["robot_error_id"] == "run-fin-0"
    assert captured["metadata"]["robot_error_signature"]
    assert captured["metadata"]["review_suite_id"] == "financial_functional_probe"
    assert "Prompt pronto" not in captured["description"]  # prompt é montado pelo agent_backlog_service
