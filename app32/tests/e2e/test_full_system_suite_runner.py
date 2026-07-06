from __future__ import annotations

from app32.tests.e2e.scripts.run_full_system_suite import (
    _apply_root_execution_env_defaults,
    _build_manifest,
    _clip_output,
    _internal_failures_from_stdout,
)


def test_full_system_runner_detects_internal_success_false_checks():
    stdout = """
[
  {
    "check_name": "meetings.root",
    "route": "/meetings/",
    "success": false,
    "status_code": 200,
    "details": {"has_public_error": true}
  },
  {
    "check_name": "meetings.company_manage",
    "route": "/meetings/company/9",
    "success": true,
    "status_code": 200
  }
]
"""

    failures = _internal_failures_from_stdout(stdout)

    assert len(failures) == 1
    assert failures[0]["check_name"] == "meetings.root"
    assert failures[0]["route"] == "/meetings/"
    assert failures[0]["status_code"] == 200


def test_full_system_runner_ignores_non_json_stdout():
    stdout = ". [100%]\n1 passed in 2.31s\n"

    assert _internal_failures_from_stdout(stdout) == []


def test_full_system_runner_clips_large_child_output():
    clipped = _clip_output("abcdef", max_chars=3)

    assert "truncado" in clipped
    assert clipped.endswith("def")


def test_full_system_runner_builds_manifest_for_robot_center():
    summary = {
        "run_id": "run_20260614_031024",
        "environment": "PROD_SAFE",
        "generated_at": "2026-06-14T03:10:24",
        "total_suites": 2,
        "passed_suites": 1,
        "failed_suites": 1,
        "results": [
            {"suite_id": "smoke_real_navigation", "domain": "smoke", "returncode": 0},
            {"suite_id": "financial_functional_probe", "domain": "financial", "returncode": 1, "internal_failures": []},
        ],
    }

    manifest = _build_manifest(summary)

    assert manifest["suite_id"] == "full_system_validation"
    assert manifest["journeys"][0]["journey"] == "smoke::smoke_real_navigation"
    assert manifest["journeys"][0]["status"] == "passed"
    assert manifest["journeys"][1]["journey"] == "financial::financial_functional_probe"
    assert manifest["journeys"][1]["status"] == "failed"
    assert manifest["journeys"][1]["failed_step"] == "suite_command"


def test_full_system_runner_injects_devfull_contract_defaults(monkeypatch):
    monkeypatch.setenv("APP32_E2E_DEV_USER_ID", "19")
    env = {}

    _apply_root_execution_env_defaults("DEV_FULL", env)

    assert env["E2E_BASE_URL"] == "http://localhost"
    assert env["E2E_COMPANY_ID"] == "10"
    assert env["E2E_USER_ID"] == "19"
    assert env["E2E_DESTRUCTIVE_ACTIONS_ALLOWED"] == "true"
    assert env["E2E_REQUIRE_EXPLICIT_COMPANY"] == "true"
    assert env["PYTHONIOENCODING"] == "utf-8"
