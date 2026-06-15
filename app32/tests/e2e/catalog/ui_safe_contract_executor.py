from __future__ import annotations

import html
import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

from app32.tests.e2e.catalog.ui_contract_generator import build_ui_human_like_contracts
from app32.tests.e2e.config.environments import load_environment_settings
from app32.tests.e2e.core.functional_guards import contains_public_error
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession


SAFE_EXECUTION_STRATEGIES = {
    "playwright_click_validate_navigation",
    "playwright_click_validate_no_public_error",
    "playwright_fill_validate",
}


@dataclass(frozen=True)
class UISafeExecutionResult:
    contract_id: str
    route: str | None
    selector: str
    action_kind: str
    execution_strategy: str
    status: str
    status_code: int | None
    mode: str
    details: dict[str, Any]


def _selector_marker(selector: str) -> tuple[str, str] | None:
    selector = str(selector or "").strip()
    if not selector:
        return None
    if selector.startswith("#"):
        return ("id", selector[1:])
    match = re.match(r"(?P<tag>[a-zA-Z0-9]+)\[name=['\"](?P<value>[^'\"]+)['\"]\]", selector)
    if match:
        return ("name", match.group("value"))
    match = re.match(r"a\[href=['\"](?P<value>[^'\"]+)['\"]\]", selector)
    if match:
        return ("href", match.group("value"))
    match = re.match(r"\[data-testid=['\"](?P<value>[^'\"]+)['\"]\]", selector)
    if match:
        return ("data-testid", match.group("value"))
    match = re.match(r"(?P<tag>[a-zA-Z0-9]+)\[type=['\"](?P<value>[^'\"]+)['\"]\]", selector)
    if match:
        return ("type", match.group("value"))
    if re.match(r"^[a-zA-Z][a-zA-Z0-9-]*$", selector):
        return ("tag", selector.lower())
    return None


def _selector_present(body: str, selector: str) -> bool:
    marker = _selector_marker(selector)
    if marker is None:
        return False
    kind, value = marker
    escaped = re.escape(html.escape(value, quote=True))
    raw = re.escape(value)
    if kind == "tag":
        return re.search(rf"<\s*{raw}(\s|>|/)", body, flags=re.IGNORECASE) is not None
    return (
        re.search(rf"{kind}\s*=\s*['\"]{escaped}['\"]", body, flags=re.IGNORECASE) is not None
        or re.search(rf"{kind}\s*=\s*['\"]{raw}['\"]", body, flags=re.IGNORECASE) is not None
    )


def _safe_contracts(limit: int) -> list[dict[str, Any]]:
    payload = build_ui_human_like_contracts()
    contracts = [
        item
        for item in payload.get("contracts") or []
        if item.get("route")
        and item.get("risk_level") == "low"
        and item.get("execution_strategy") in SAFE_EXECUTION_STRATEGIES
        and not item.get("requires_company_id")
        and not item.get("requires_human_gate")
    ]
    contracts.sort(key=lambda item: (str(item.get("route") or ""), str(item.get("priority") or ""), str(item.get("contract_id") or "")))
    return contracts[:limit]


def execute_ui_safe_contracts(*, limit: int | None = None) -> dict[str, Any]:
    settings = load_environment_settings()
    limit = int(limit or os.environ.get("E2E_UI_SAFE_CONTRACT_LIMIT") or 80)
    http = AuthenticatedHTTPSession.create(settings)
    http.login()
    http.select_company()

    contracts = _safe_contracts(limit)
    route_cache: dict[str, tuple[int, str, str]] = {}
    results: list[UISafeExecutionResult] = []

    for contract in contracts:
        route = str(contract.get("route") or "")
        if route not in route_cache:
            try:
                response = http.request("GET", route)
                http.assert_not_login_redirect(response, operation=f"ui_safe.{route}")
                route_cache[route] = (
                    int(response.status_code),
                    str(response.headers.get("Content-Type") or ""),
                    response.text or "",
                )
            except Exception as exc:
                results.append(
                    UISafeExecutionResult(
                        contract_id=str(contract.get("contract_id")),
                        route=route,
                        selector=str(contract.get("selector") or ""),
                        action_kind=str(contract.get("action_kind") or ""),
                        execution_strategy=str(contract.get("execution_strategy") or ""),
                        status="failed",
                        status_code=None,
                        mode="http_authenticated_safe_execution",
                        details={"error": str(exc), "phase": "route_open"},
                    )
                )
                continue

        status_code, content_type, body = route_cache[route]
        is_html = "html" in content_type.lower()
        has_public_error = contains_public_error(body)
        selector_ok = _selector_present(body, str(contract.get("selector") or ""))
        ok = 200 <= status_code < 400 and is_html and not has_public_error and selector_ok
        mode = {
            "playwright_fill_validate": "http_render_presence_fill_contract",
            "playwright_click_validate_navigation": "http_render_presence_navigation_contract",
            "playwright_click_validate_no_public_error": "http_render_presence_click_contract",
        }.get(str(contract.get("execution_strategy") or ""), "http_render_presence_contract")
        results.append(
            UISafeExecutionResult(
                contract_id=str(contract.get("contract_id")),
                route=route,
                selector=str(contract.get("selector") or ""),
                action_kind=str(contract.get("action_kind") or ""),
                execution_strategy=str(contract.get("execution_strategy") or ""),
                status="passed" if ok else "failed",
                status_code=status_code,
                mode=mode,
                details={
                    "content_type": content_type,
                    "selector_present": selector_ok,
                    "has_public_error": has_public_error,
                    "risk_level": contract.get("risk_level"),
                    "priority": contract.get("priority"),
                    "non_persistent": True,
                    "no_submit": True,
                    "no_mutation": True,
                },
            )
        )

    status_counts = Counter(item.status for item in results)
    strategy_counts = Counter(item.execution_strategy for item in results)
    failed = [item for item in results if item.status != "passed"]
    return {
        "generated_at": datetime.now().isoformat(),
        "environment": settings.environment_name,
        "company_id": settings.company_id,
        "limit": limit,
        "selected_contracts_total": len(contracts),
        "executed_contracts_total": len(results),
        "passed_contracts_total": status_counts.get("passed", 0),
        "failed_contracts_total": status_counts.get("failed", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "execution_strategy_counts": dict(sorted(strategy_counts.items())),
        "routes_opened_total": len(route_cache),
        "non_persistent": True,
        "mutation_contracts_executed": 0,
        "results": [asdict(item) for item in results],
        "failed_results": [asdict(item) for item in failed[:100]],
    }


def write_ui_safe_execution_report(base_dir: Path) -> Path:
    report = execute_ui_safe_contracts()
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = base_dir / "ui_safe_execution" / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "ui_safe_execution.json"
    yaml_path = target_dir / "ui_safe_execution.yaml"
    summary_path = target_dir / "summary.json"
    manifest_path = target_dir / "manifest.json"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if yaml is not None:
        yaml_path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        yaml_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "generated_at": report["generated_at"],
        "environment": report["environment"],
        "company_id": report["company_id"],
        "selected_contracts_total": report["selected_contracts_total"],
        "executed_contracts_total": report["executed_contracts_total"],
        "passed_contracts_total": report["passed_contracts_total"],
        "failed_contracts_total": report["failed_contracts_total"],
        "routes_opened_total": report["routes_opened_total"],
        "mutation_contracts_executed": report["mutation_contracts_executed"],
        "non_persistent": report["non_persistent"],
        "json_path": str(json_path),
        "yaml_path": str(yaml_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "environment": report["environment"],
                "generated_at": report["generated_at"],
                "suite_id": "ui_safe_contract_execution",
                "journeys": [
                    {
                        "journey": "governance::ui_safe_contract_execution",
                        "suite_id": "ui_safe_contract_execution",
                        "domain": "governance",
                        "status": "failed" if report["failed_contracts_total"] else "passed",
                        "failed_step": "safe_contract_presence" if report["failed_contracts_total"] else None,
                        "failure_type": "assertion" if report["failed_contracts_total"] else None,
                        "company_id": report["company_id"],
                    }
                ],
                "events": [{"event": "ui_safe_contract_execution_completed", **summary}],
                "artifacts": [{"kind": "ui_safe_execution", "path": "ui_safe_execution.json"}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_path
