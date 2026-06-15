from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings
from app32.tests.e2e.config.smoke_targets import SMOKE_TARGETS
from app32.tests.e2e.core.functional_guards import contains_public_error
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


@dataclass(frozen=True)
class SmokeNavigationProbeResult:
    check_name: str
    route: str
    success: bool
    status_code: int
    details: dict[str, Any]


def _run_browser_smoke_for_dev_full() -> int:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "app32/tests/e2e/journeys/smoke/test_real_navigation_smoke.py",
            "-q",
        ],
        cwd=str(ROOT_DIR),
        env=env,
        check=False,
    )
    return int(completed.returncode)


def _execute_prod_safe_http_smoke() -> list[SmokeNavigationProbeResult]:
    settings = load_environment_settings()
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    results: list[SmokeNavigationProbeResult] = []
    for target in SMOKE_TARGETS[1:]:
        response = http.request("GET", target.route)
        http.assert_not_login_redirect(response, operation=f"smoke.{target.key}")
        content_type = str(response.headers.get("Content-Type") or "")
        body = response.text or ""
        expected_fragment_ok = target.expected_url_fragment in str(response.url or "")
        public_error = contains_public_error(body)
        success = (
            response.ok
            and expected_fragment_ok
            and "html" in content_type.lower()
            and not public_error
        )
        results.append(
            SmokeNavigationProbeResult(
                check_name=f"smoke.{target.key}",
                route=target.route,
                success=success,
                status_code=response.status_code,
                details={
                    "final_url": response.url,
                    "expected_url_fragment": target.expected_url_fragment,
                    "content_type": content_type,
                    "content_length": len(body),
                    "has_public_error": public_error,
                    "mode": "prod_safe_http_navigation",
                },
            )
        )
    return results


def main() -> int:
    settings = load_environment_settings()
    if settings.execution_mode is not E2EExecutionMode.PROD_SAFE:
        return _run_browser_smoke_for_dev_full()

    results = _execute_prod_safe_http_smoke()
    print(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
    return 0 if all(item.success for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
