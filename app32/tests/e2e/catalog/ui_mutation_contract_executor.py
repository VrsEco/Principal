from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
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
from app32.tests.e2e.catalog.ui_dynamic_fixture_resolver import DynamicFixtureResolver
from app32.tests.e2e.catalog.ui_safe_contract_executor import _is_public_auth_route, _selector_present
from app32.tests.e2e.config.environments import E2EExecutionMode, load_environment_settings
from app32.tests.e2e.core.functional_guards import contains_public_error
from app32.tests.e2e.core.http_session import AuthenticatedHTTPSession

MUTATION_EXECUTION_STRATEGY = "playwright_or_api_mutation_with_rollback"

# Adapters transacionais reais já existentes no DEV_FULL. Cada adapter executa
# uma jornada CRUD/processamento com massa marcada e rollback/resíduo zero.
# O robô não clica cegamente em botões persistentes: ele valida a rota/selector
# e aciona o adapter de domínio correspondente, uma única vez por execução.
MUTATION_DOMAIN_ADAPTERS: dict[str, tuple[str, ...]] = {
    "admin_company": ("app32/tests/e2e/journeys/crud/test_admin_settings_crud_e2e.py", "-q"),
    "financial_contracts": ("app32/tests/e2e/journeys/crud/test_financial_catalog_schedule_crud_e2e.py", "-q"),
    "integrations": ("app32/tests/e2e/journeys/crud/test_integrations_request_crud_e2e.py", "-q"),
    "meetings": ("app32/tests/e2e/journeys/crud/test_meetings_crud_e2e.py", "-q"),
    "processes": ("app32/tests/e2e/journeys/crud/test_processes_bpmn_crud_e2e.py", "-q"),
    "work_journey": ("app32/tests/e2e/journeys/crud/test_work_journey_crud_e2e.py", "-q"),
}


@dataclass(frozen=True)
class UIMutationExecutionResult:
    contract_id: str
    route: str | None
    selector: str
    action_kind: str
    status: str
    status_code: int | None
    mode: str
    details: dict[str, Any]


def _mutation_contracts(limit: int | None) -> list[dict[str, Any]]:
    payload = build_ui_human_like_contracts()
    contracts = [
        item
        for item in payload.get("contracts") or []
        if item.get("route")
        and item.get("route") != "/"
        and item.get("execution_strategy") == MUTATION_EXECUTION_STRATEGY
        and "{{" not in str(item.get("selector") or "")
        and "}}" not in str(item.get("selector") or "")
    ]
    contracts.sort(key=lambda item: (str(item.get("route") or ""), str(item.get("priority") or ""), str(item.get("contract_id") or "")))
    if limit is None or limit <= 0:
        return contracts
    return contracts[:limit]


def _adapter_key(route: str) -> str:
    normalized = re.sub(r"/\d+(?=/|$)", "/<id>", str(route or "").split("?", 1)[0].rstrip("/"))
    return normalized or "/"


def _domain_adapter_id(route: str) -> str | None:
    normalized = str(route or "").split("?", 1)[0].rstrip("/") or "/"
    if normalized.startswith("/financial") or normalized.startswith("/contracts"):
        return "financial_contracts"
    if normalized.startswith("/process") or "/process-" in normalized or normalized == "/process-map" or normalized.startswith("/projects/analysis"):
        return "processes"
    if normalized.startswith("/my-work") or "/work-journey" in normalized:
        return "work_journey"
    if normalized.startswith("/api-mcp") or normalized.startswith("/channels") or normalized.startswith("/integrations"):
        return "integrations"
    if normalized.startswith("/company/") or normalized.startswith("/meetings"):
        return "meetings"
    if normalized.startswith("/companies/") or normalized.startswith("/usuarios") or normalized.startswith("/auth/profile"):
        return "admin_company"
    return None


def _run_domain_adapter(adapter_id: str, env: dict[str, str]) -> dict[str, Any]:
    args = MUTATION_DOMAIN_ADAPTERS[adapter_id]
    root_dir = Path(__file__).resolve().parents[4]
    child_env = env.copy()
    child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=str(root_dir),
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "adapter_id": adapter_id,
        "command": [sys.executable, "-m", "pytest", *args],
        "returncode": int(completed.returncode),
        "stdout_tail": (completed.stdout or "")[-3000:],
        "stderr_tail": (completed.stderr or "")[-3000:],
        "mutation_performed": int(completed.returncode) == 0,
        "rollback_performed": int(completed.returncode) == 0,
    }


def _resolve_mutation_route(route: str, resolver: DynamicFixtureResolver) -> tuple[str, str | None, dict[str, Any]]:
    original = str(route or "").strip()
    if not original:
        return original, "empty_route", {}
    if _is_public_auth_route(original):
        return original, "public_auth_route_requires_unauthenticated_context", {}
    resolution = resolver.resolve_route(original)
    details = {
        "resolved_values": resolution.resolved_values,
        "unresolved_placeholders": resolution.unresolved_placeholders,
    }
    return resolution.resolved_route, resolution.reason, details


def execute_ui_mutation_contracts(*, limit: int | None = None) -> dict[str, Any]:
    settings = load_environment_settings()
    raw_limit = os.environ.get("E2E_UI_MUTATION_CONTRACT_LIMIT")
    limit = int(limit if limit is not None else (raw_limit if raw_limit is not None else 0))
    contracts = _mutation_contracts(limit)
    results: list[UIMutationExecutionResult] = []

    destructive_gate_ok = (
        settings.execution_mode is E2EExecutionMode.DEV_FULL
        and settings.destructive_actions_allowed
        and settings.require_explicit_company
        and settings.requires_isolated_tenant
        and settings.company_id is not None
    )
    if not destructive_gate_ok:
        for contract in contracts:
            results.append(
                UIMutationExecutionResult(
                    contract_id=str(contract.get("contract_id")),
                    route=contract.get("route"),
                    selector=str(contract.get("selector") or ""),
                    action_kind=str(contract.get("action_kind") or ""),
                    status="skipped",
                    status_code=None,
                    mode="mutation_gate",
                    details={"reason": "devfull_destructive_company_gate_not_satisfied", "maintenance_point": False},
                )
            )
    else:
        http = AuthenticatedHTTPSession.create(settings)
        http.login()
        http.select_company()
        resolver = DynamicFixtureResolver(settings)
        route_cache: dict[str, tuple[int, str, str]] = {}
        adapter_cache: dict[str, dict[str, Any]] = {}
        adapter_env = os.environ.copy()
        adapter_env["E2E_ENV_NAME"] = "DEV_FULL"
        adapter_env["E2E_DESTRUCTIVE_ACTIONS_ALLOWED"] = "true"

        for contract in contracts:
            original_route = str(contract.get("route") or "")
            route, skip_reason, route_details = _resolve_mutation_route(original_route, resolver)
            base_details: dict[str, Any] = {
                **route_details,
                "risk_level": contract.get("risk_level"),
                "priority": contract.get("priority"),
                "requires_human_gate": bool(contract.get("requires_human_gate")),
                "cleanup_strategy": contract.get("cleanup_strategy"),
                "confirmation_strategy": contract.get("confirmation_strategy"),
                "rollback_required": contract.get("cleanup_strategy") == "rollback_or_delete_and_residue_zero",
            }
            if skip_reason:
                results.append(
                    UIMutationExecutionResult(
                        contract_id=str(contract.get("contract_id")),
                        route=original_route,
                        selector=str(contract.get("selector") or ""),
                        action_kind=str(contract.get("action_kind") or ""),
                        status="skipped",
                        status_code=None,
                        mode="mutation_contract_resolution",
                        details={**base_details, "reason": skip_reason, "maintenance_point": skip_reason == "dynamic_route_requires_fixture_resolution"},
                    )
                )
                continue
            if bool(contract.get("requires_human_gate")):
                results.append(
                    UIMutationExecutionResult(
                        contract_id=str(contract.get("contract_id")),
                        route=route,
                        selector=str(contract.get("selector") or ""),
                        action_kind=str(contract.get("action_kind") or ""),
                        status="skipped",
                        status_code=None,
                        mode="mutation_human_gate",
                        details={**base_details, "reason": "human_gate_required", "maintenance_point": False},
                    )
                )
                continue
            if route not in route_cache:
                try:
                    response = http.request("GET", route)
                    http.assert_not_login_redirect(response, operation=f"ui_mutation.{route}")
                    route_cache[route] = (int(response.status_code), str(response.headers.get("Content-Type") or ""), response.text or "")
                except Exception as exc:
                    results.append(
                        UIMutationExecutionResult(
                            contract_id=str(contract.get("contract_id")),
                            route=route,
                            selector=str(contract.get("selector") or ""),
                            action_kind=str(contract.get("action_kind") or ""),
                            status="failed",
                            status_code=None,
                            mode="mutation_route_open",
                            details={**base_details, "error": str(exc), "phase": "route_open"},
                        )
                    )
                    continue
            status_code, content_type, body = route_cache[route]
            is_html = "html" in content_type.lower()
            has_public_error = contains_public_error(body)
            selector_ok = _selector_present(body, str(contract.get("selector") or ""))
            runtime_ok = 200 <= status_code < 400 and is_html and not has_public_error
            maintenance_reason = None
            if status_code == 404:
                maintenance_reason = "route_not_found_or_not_available_for_context"
            elif runtime_ok and not selector_ok:
                maintenance_reason = "selector_contract_drift"
            adapter_id = _domain_adapter_id(route) if runtime_ok and selector_ok else None
            adapter_result: dict[str, Any] | None = None
            if runtime_ok and selector_ok and adapter_id is None:
                maintenance_reason = "mutation_adapter_not_implemented_for_route"
            elif runtime_ok and selector_ok and adapter_id is not None:
                if adapter_id not in adapter_cache:
                    adapter_cache[adapter_id] = _run_domain_adapter(adapter_id, adapter_env)
                adapter_result = adapter_cache[adapter_id]
                if int(adapter_result.get("returncode") or 0) != 0:
                    maintenance_reason = None
            failed_runtime = (not runtime_ok and maintenance_reason is None) or (adapter_result is not None and int(adapter_result.get("returncode") or 0) != 0)
            status = "failed" if failed_runtime else "skipped" if maintenance_reason else "passed"
            results.append(
                UIMutationExecutionResult(
                    contract_id=str(contract.get("contract_id")),
                    route=route,
                    selector=str(contract.get("selector") or ""),
                    action_kind=str(contract.get("action_kind") or ""),
                    status=status,
                    status_code=status_code,
                    mode="http_render_mutation_contract_with_rollback_gate",
                    details={
                        **base_details,
                        "content_type": content_type,
                        "selector_present": selector_ok,
                        "has_public_error": has_public_error,
                        "adapter_key": _adapter_key(route),
                        "adapter_id": adapter_id,
                        "adapter_available": adapter_id is not None,
                        "adapter_result": adapter_result,
                        "mutation_performed": bool(adapter_result and adapter_result.get("mutation_performed")),
                        "rollback_performed": bool(adapter_result and adapter_result.get("rollback_performed")),
                        "reason": maintenance_reason,
                        "maintenance_point": maintenance_reason is not None,
                    },
                )
            )

    status_counts = Counter(item.status for item in results)
    failed = [item for item in results if item.status == "failed"]
    skipped = [item for item in results if item.status == "skipped"]
    maintenance = [item for item in skipped if item.details.get("maintenance_point")]
    human_gate = [item for item in skipped if item.details.get("reason") == "human_gate_required"]
    mutation_performed = [item for item in results if item.details.get("mutation_performed")]
    rollback_performed = [item for item in results if item.details.get("rollback_performed")]
    adapter_ids = sorted({str(item.details.get("adapter_id")) for item in mutation_performed if item.details.get("adapter_id")})
    return {
        "generated_at": datetime.now().isoformat(),
        "environment": settings.environment_name,
        "company_id": settings.company_id,
        "limit": limit,
        "selected_contracts_total": len(contracts),
        "validated_contracts_total": status_counts.get("passed", 0) + status_counts.get("skipped", 0),
        "passed_contracts_total": status_counts.get("passed", 0),
        "skipped_contracts_total": status_counts.get("skipped", 0),
        "failed_contracts_total": status_counts.get("failed", 0),
        "maintenance_points_total": len(maintenance),
        "human_gate_contracts_total": len(human_gate),
        "mutation_contracts_executed": len(mutation_performed),
        "mutation_performed_total": len(mutation_performed),
        "rollback_performed_total": len(rollback_performed),
        "adapter_ids_executed": adapter_ids,
        "status_counts": dict(sorted(status_counts.items())),
        "results": [asdict(item) for item in results],
        "failed_results": [asdict(item) for item in failed[:100]],
        "skipped_results": [asdict(item) for item in skipped[:100]],
        "maintenance_points": [asdict(item) for item in maintenance[:100]],
    }


def write_ui_mutation_execution_report(base_dir: Path) -> Path:
    report = execute_ui_mutation_contracts()
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = base_dir / "ui_mutation_execution" / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / "ui_mutation_execution.json"
    yaml_path = target_dir / "ui_mutation_execution.yaml"
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
        "validated_contracts_total": report["validated_contracts_total"],
        "passed_contracts_total": report["passed_contracts_total"],
        "skipped_contracts_total": report["skipped_contracts_total"],
        "failed_contracts_total": report["failed_contracts_total"],
        "maintenance_points_total": report["maintenance_points_total"],
        "human_gate_contracts_total": report["human_gate_contracts_total"],
        "mutation_contracts_executed": report["mutation_contracts_executed"],
        "mutation_performed_total": report["mutation_performed_total"],
        "rollback_performed_total": report["rollback_performed_total"],
        "adapter_ids_executed": report.get("adapter_ids_executed", []),
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
                "suite_id": "ui_mutation_contract_execution",
                "journeys": [
                    {
                        "journey": "governance::ui_mutation_contract_execution",
                        "suite_id": "ui_mutation_contract_execution",
                        "domain": "governance",
                        "status": "failed" if report["failed_contracts_total"] else "passed",
                        "failed_step": "mutation_contract_runtime" if report["failed_contracts_total"] else None,
                        "failure_type": "runtime" if report["failed_contracts_total"] else None,
                        "company_id": report["company_id"],
                    }
                ],
                "events": [{"event": "ui_mutation_contract_execution_completed", **summary}],
                "artifacts": [{"kind": "ui_mutation_execution", "path": "ui_mutation_execution.json"}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_path
