from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.catalog.suite_catalog import E2ESuiteDefinition, list_suite_catalog

EXCLUDED_FULL_RUN_SUITES = {"inventory_system_scan", "full_system_validation"}
VIRTUAL_AGGREGATE_SUITES = {"devfull_transactional_validation", "devfull_full_app_validation"}


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    stdout_original_chars: int
    stderr_original_chars: int

TRANSACTIONAL_DEPENDENCIES = {
    "meetings_crud_devfull",
    "work_journey_manual_task_crud_devfull",
    "admin_performance_settings_transactional_devfull",
    "processes_bpmn_diagram_transactional_devfull",
    "financial_catalog_schedule_transactional_devfull",
    "integrations_request_transactional_devfull",
}

FULL_APP_DEPENDENCIES = {
    "ui_inventory_contract_scan",
    "ui_human_like_contract_generation",
    "ui_safe_contract_execution",
    "ui_mutation_contract_execution",
    "smoke_real_navigation",
    "workspace_functional_probe",
    "integrations_functional_probe",
    "meetings_functional_probe",
    "work_journey_functional_probe",
    "processes_functional_probe",
    "financial_functional_probe",
    "contracts_functional_probe",
    "contracts_tenant_contract_probe",
    "workspace_tenant_contract_probe",
    "consultive_tenant_contract_probe",
    "reports_functional_probe",
    "admin_functional_probe",
    "mcp_http_health_probe",
    "full_coverage_autocorrect_audit",
    "user_concurrency_probe",
    "mcp_concurrency_probe",
    "devfull_transactional_validation",
    "drift_detection",
}

AGGREGATE_DEPENDENCIES = {
    "devfull_transactional_validation": TRANSACTIONAL_DEPENDENCIES,
    "devfull_full_app_validation": FULL_APP_DEPENDENCIES,
}


def _set_env_default(env: dict[str, str], key: str, value: str | None) -> None:
    if value is not None and not str(env.get(key) or "").strip():
        env[key] = str(value)


def _resolve_devfull_default_user_id() -> str | None:
    configured = str(os.environ.get("APP32_E2E_DEV_USER_ID") or "").strip()
    if configured.isdigit():
        return configured
    try:
        from app import create_app
        from models.user import User

        app = create_app(os.environ.get("FLASK_CONFIG") or "development")
        with app.app_context():
            preferred = (
                User.query.filter(
                    User.email.in_(
                        (
                            "admin@gestaoversus.com.br",
                            "teste@gestaoversus.com.br",
                            "mff2000@gmail.com",
                        )
                    ),
                    User.role == "admin",
                    User.is_active.is_(True),
                )
                .order_by(User.id.asc())
                .first()
            )
            if preferred:
                return str(int(preferred.id))
            active_admin = User.query.filter_by(role="admin", is_active=True).order_by(User.id.asc()).first()
            return str(int(active_admin.id)) if active_admin else None
    except Exception:
        return None


def _apply_root_execution_env_defaults(environment: str, env: dict[str, str]) -> None:
    normalized = str(environment or "").strip().upper()
    _set_env_default(env, "PYTHONIOENCODING", "utf-8")
    _set_env_default(env, "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    _set_env_default(env, "E2E_LOGIN_PATH", "/login")
    _set_env_default(env, "E2E_POST_LOGIN_PATH", "/my-work")
    _set_env_default(env, "APP_BOOTSTRAP_DB_SCHEMA", "0")
    _set_env_default(env, "APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
    _set_env_default(env, "E2E_HEADLESS", "true")
    _set_env_default(env, "E2E_REQUIRES_ISOLATED_TENANT", "true")
    _set_env_default(env, "E2E_REQUIRE_EXPLICIT_COMPANY", "true")
    _set_env_default(env, "E2E_SUITE_TIMEOUT_SECONDS", "600")
    if normalized == "DEV_FULL":
        _set_env_default(env, "E2E_BASE_URL", "http://localhost")
        _set_env_default(env, "E2E_COMPANY_ID", os.environ.get("APP32_E2E_DEV_COMPANY_ID") or "10")
        _set_env_default(env, "E2E_USER_ID", _resolve_devfull_default_user_id())
        _set_env_default(env, "E2E_DESTRUCTIVE_ACTIONS_ALLOWED", "true")


def _max_captured_output_chars() -> int:
    return int(os.environ.get("E2E_RESULT_OUTPUT_MAX_CHARS") or 20000)


def _clip_output(text: str, *, max_chars: int | None = None) -> str:
    limit = max_chars if max_chars is not None else _max_captured_output_chars()
    value = str(text or "")
    if limit <= 0 or len(value) <= limit:
        return value
    return (
        f"[stdout/stderr truncado: {len(value)} caracteres originais; "
        f"mantendo os últimos {limit}]\n"
        f"{value[-limit:]}"
    )


def _read_limited_process_output(path: Path, *, max_chars: int | None = None) -> tuple[str, int]:
    """Lê saída de subprocesso sem carregar arquivos gigantes em memória.

    O DEV_FULL pode produzir stdout/stderr muito grandes em suítes de UI. Na
    Central em produção, manter esses buffers em memória junto do uWSGI elevou
    risco de OOM. Para preservar o diagnóstico, mantemos a saída completa só
    quando ela já está dentro do limite operacional; acima disso, lemos apenas
    a cauda e anotamos o tamanho original aproximado em caracteres.
    """
    limit = max_chars if max_chars is not None else _max_captured_output_chars()
    if not path.exists():
        return "", 0
    size_bytes = path.stat().st_size
    if limit <= 0 or size_bytes <= limit:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text, len(text)

    read_bytes = max(limit * 4, 4096)
    with path.open("rb") as handle:
        handle.seek(max(size_bytes - read_bytes, 0))
        raw = handle.read()
    text = raw.decode("utf-8", errors="replace")
    if len(text) > limit:
        text = text[-limit:]
    approx_original_chars = size_bytes
    return _clip_output(text, max_chars=limit), approx_original_chars


def _decode_stdout_json(stdout: str) -> object | None:
    text = str(stdout or "").strip()
    if not text:
        return None
    start_positions = [pos for pos in (text.find("["), text.find("{")) if pos >= 0]
    if not start_positions:
        return None
    start = min(start_positions)
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(text[start:])
        return payload
    except json.JSONDecodeError:
        return None


def _collect_failed_success_checks(payload: object, *, path: str = "$") -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    if isinstance(payload, dict):
        if payload.get("success") is False:
            failures.append(
                {
                    "path": path,
                    "check_name": payload.get("check_name"),
                    "route": payload.get("route") or payload.get("endpoint"),
                    "status_code": payload.get("status_code"),
                    "details": payload.get("details"),
                }
            )
        for key, value in payload.items():
            failures.extend(_collect_failed_success_checks(value, path=f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            failures.extend(_collect_failed_success_checks(value, path=f"{path}[{index}]"))
    return failures


def _internal_failures_from_stdout(stdout: str) -> list[dict[str, object]]:
    payload = _decode_stdout_json(stdout)
    if payload is None:
        return []
    return _collect_failed_success_checks(payload)


def _print_json_utf8(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()


def _build_manifest(summary: dict[str, object]) -> dict[str, object]:
    """Converte o resumo do teste completo para o contrato operacional E2E.

    A Central do Robô lê `manifest.json`; sem este arquivo a execução completa
    terminava rápido, mas não atualizava as áreas funcionais na tela.
    """
    journeys: list[dict[str, object]] = []
    for result in summary.get("results") or []:
        if not isinstance(result, dict):
            continue
        returncode = int(result.get("returncode") or 0)
        failed_step = None
        failure_type = None
        if returncode != 0:
            failure_type = "assertion" if result.get("internal_failures") else "runtime"
            failed_step = "internal_success_check" if result.get("internal_failures") else "suite_command"
        journeys.append(
            {
                "journey": f"{result.get('domain') or 'system'}::{result.get('suite_id')}",
                "status": "passed" if returncode == 0 else "failed",
                "suite_id": result.get("suite_id"),
                "domain": result.get("domain"),
                "failed_step": failed_step,
                "failure_type": failure_type,
                "company_id": os.environ.get("E2E_COMPANY_ID"),
            }
        )
    return {
        "run_id": summary.get("run_id"),
        "environment": summary.get("environment"),
        "generated_at": summary.get("generated_at"),
        "suite_id": "full_system_validation",
        "journeys": journeys,
        "events": [
            {
                "event": "full_system_suite_completed",
                "total_suites": summary.get("total_suites"),
                "passed_suites": summary.get("passed_suites"),
                "failed_suites": summary.get("failed_suites"),
            }
        ],
        "artifacts": [
            {
                "kind": "summary",
                "path": "summary.json",
            }
        ],
    }


def _order_suites_for_root_orchestration(suites: list[E2ESuiteDefinition]) -> list[E2ESuiteDefinition]:
    """Executa suítes atômicas primeiro e agregadores virtuais no fim.

    O teste completo é o orquestrador raiz. Executar agregadores como processo
    filho fazia o DEV_FULL repetir suítes mutacionais inteiras e, em Windows,
    criar cadeias longas de subprocessos propensas a timeout. Neste nível, os
    agregadores são checagens de cobertura sobre resultados já produzidos.
    """
    atomic = [suite for suite in suites if suite.suite_id not in VIRTUAL_AGGREGATE_SUITES]
    aggregates = [suite for suite in suites if suite.suite_id in VIRTUAL_AGGREGATE_SUITES]
    return [*atomic, *aggregates]


def _virtual_aggregate_result(
    suite: E2ESuiteDefinition,
    *,
    results_by_suite_id: dict[str, dict[str, object]],
) -> dict[str, object]:
    dependency_ids = sorted(AGGREGATE_DEPENDENCIES.get(suite.suite_id) or set())
    missing = [suite_id for suite_id in dependency_ids if suite_id not in results_by_suite_id]
    failed = [
        suite_id
        for suite_id in dependency_ids
        if int((results_by_suite_id.get(suite_id) or {}).get("returncode") or 0) != 0
    ]
    returncode = 1 if missing or failed else 0
    payload = {
        "suite_id": suite.suite_id,
        "label": suite.label,
        "domain": suite.domain,
        "returncode": returncode,
        "process_returncode": 0,
        "virtual_aggregate": True,
        "covered_suite_ids": dependency_ids,
        "missing_suite_ids": missing,
        "failed_dependency_suite_ids": failed,
        "internal_failures": [],
        "stdout": json.dumps(
            {
                "suite_id": suite.suite_id,
                "success": returncode == 0,
                "mode": "root_orchestrator_virtual_aggregate",
                "covered_suite_ids": dependency_ids,
                "missing_suite_ids": missing,
                "failed_dependency_suite_ids": failed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        "stderr": "",
    }
    return payload


def _suite_timeout_seconds(suite_id: str | None = None) -> int:
    if suite_id in {"devfull_full_app_validation"}:
        return int(os.environ.get("E2E_FULL_APP_SUITE_TIMEOUT_SECONDS") or os.environ.get("E2E_SUITE_TIMEOUT_SECONDS") or 1200)
    if suite_id in {"devfull_transactional_validation", "ui_safe_contract_execution", "ui_mutation_contract_execution"}:
        return int(os.environ.get("E2E_TRANSACTIONAL_SUITE_TIMEOUT_SECONDS") or os.environ.get("E2E_SUITE_TIMEOUT_SECONDS") or 600)
    return int(os.environ.get("E2E_SUITE_TIMEOUT_SECONDS") or 300)


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        return
    process.kill()


def _run_command_with_timeout(command: list[str], *, env: dict[str, str], suite_id: str | None = None) -> CommandResult:
    timeout_seconds = _suite_timeout_seconds(suite_id)
    with tempfile.TemporaryDirectory(prefix="gv-e2e-suite-") as temp_dir:
        stdout_path = Path(temp_dir) / "stdout.log"
        stderr_path = Path(temp_dir) / "stderr.log"
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT_DIR),
                env=env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            try:
                process.wait(timeout=timeout_seconds)
                returncode = int(process.returncode or 0)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process)
                process.wait()
                returncode = 124
                stderr_handle.write(f"\nTimeoutExpired: suíte excedeu {timeout_seconds}s.\n".encode("utf-8"))

        stdout, stdout_original_chars = _read_limited_process_output(stdout_path)
        stderr, stderr_original_chars = _read_limited_process_output(stderr_path)
        return CommandResult(
            args=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_original_chars=stdout_original_chars,
            stderr_original_chars=stderr_original_chars,
        )


def main() -> int:
    environment = str(os.environ.get("E2E_ENV_NAME") or "DEV_FULL").strip().upper()
    suites = _order_suites_for_root_orchestration([
        suite for suite in list_suite_catalog()
        if environment in suite.environments and suite.suite_id not in EXCLUDED_FULL_RUN_SUITES
    ])

    env = os.environ.copy()
    _apply_root_execution_env_defaults(environment, env)
    results: list[dict[str, object]] = []
    results_by_suite_id: dict[str, dict[str, object]] = {}
    for suite in suites:
        if suite.suite_id in VIRTUAL_AGGREGATE_SUITES:
            result = _virtual_aggregate_result(suite, results_by_suite_id=results_by_suite_id)
            results.append(result)
            results_by_suite_id[suite.suite_id] = result
            continue

        if suite.command_kind == "pytest":
            env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            command = [sys.executable, "-m", "pytest", *suite.command_args]
        elif suite.command_kind == "python":
            command = [sys.executable, *suite.command_args]
        else:
            raise RuntimeError(f"command_kind não suportado: {suite.command_kind}")

        suite_env = env.copy()
        if suite.suite_id == "ui_mutation_contract_execution":
            # No orquestrador raiz, a cobertura mutacional real vem das suítes
            # transacionais DEV_FULL atômicas executadas no mesmo ciclo. A suíte
            # de contratos UI deve validar rotas/selectors/adapters sem
            # reexecutar todo o pacote transacional como subprocesso aninhado,
            # evitando pico de memória/OOM no host Configr.
            suite_env["E2E_UI_MUTATION_DEFER_ADAPTER_EXECUTION"] = "1"

        completed = _run_command_with_timeout(command, env=suite_env, suite_id=suite.suite_id)
        internal_failures = _internal_failures_from_stdout(completed.stdout)
        effective_returncode = completed.returncode if completed.returncode != 0 or not internal_failures else 1
        results.append(
            {
                "suite_id": suite.suite_id,
                "label": suite.label,
                "domain": suite.domain,
                "returncode": effective_returncode,
                "process_returncode": completed.returncode,
                "internal_failures": internal_failures,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "stdout_original_chars": completed.stdout_original_chars,
                "stderr_original_chars": completed.stderr_original_chars,
            }
        )
        results_by_suite_id[suite.suite_id] = results[-1]

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    target_dir = ROOT_DIR / "app32" / "tests" / "e2e" / "outputs" / "full_system" / environment.lower() / run_id / "reports"
    target_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_id": run_id,
        "environment": environment,
        "generated_at": datetime.now().isoformat(),
        "total_suites": len(results),
        "passed_suites": sum(1 for item in results if item["returncode"] == 0),
        "failed_suites": sum(1 for item in results if item["returncode"] != 0),
        "failed_suite_ids": [item["suite_id"] for item in results if item["returncode"] != 0],
        "results": results,
    }
    summary_path = target_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(_build_manifest(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    _print_json_utf8(summary)
    return 0 if summary["failed_suites"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
