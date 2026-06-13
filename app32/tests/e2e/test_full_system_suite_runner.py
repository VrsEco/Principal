from __future__ import annotations

from app32.tests.e2e.scripts.run_full_system_suite import _internal_failures_from_stdout


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

