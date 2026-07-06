from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _read_payload(meta_path: Path) -> dict[str, Any]:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _write_payload(meta_path: Path, payload: dict[str, Any]) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = meta_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(meta_path)


def _decode_stdout_json(stdout_path: Path) -> Any:
    try:
        text = stdout_path.read_text(encoding="utf-8", errors="ignore").strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    start_positions = [pos for pos in (text.find("["), text.find("{")) if pos >= 0]
    if not start_positions:
        return None
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(text[min(start_positions):])
        return payload
    except json.JSONDecodeError:
        return None


def _payload_has_failure(payload: Any) -> bool:
    if isinstance(payload, dict):
        if payload.get("failed_suites") or payload.get("returncode") not in {None, 0}:
            return True
        if payload.get("success") is False:
            return True
        return any(_payload_has_failure(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_payload_has_failure(item) for item in payload)
    return False


def _infer_artifact_paths(payload: Any, workdir: Path, environment: str) -> tuple[str | None, str | None]:
    run_id = payload.get("run_id") if isinstance(payload, dict) else None
    if not run_id:
        return None, None
    outputs_dir = workdir / "app32" / "tests" / "e2e" / "outputs"
    suite_id = str(payload.get("suite_id") or "") if isinstance(payload, dict) else ""
    if suite_id == "full_coverage_autocorrect_audit" or payload.get("coverage_gaps_total") is not None:
        reports_dir = outputs_dir / "full_coverage_autocorrect" / str(run_id) / "reports"
    else:
        reports_dir = outputs_dir / "full_system" / environment.lower() / str(run_id) / "reports"
    summary_path = reports_dir / "summary.json"
    manifest_path = reports_dir / "manifest.json"
    return (
        str(summary_path) if summary_path.exists() else None,
        str(manifest_path) if manifest_path.exists() else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker desacoplado para execução E2E supervisionada.")
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--stdout-path", required=True)
    parser.add_argument("--stderr-path", required=True)
    parser.add_argument("--meta-path", required=True)
    args = parser.parse_args()

    command = json.loads(args.command_json)
    workdir = Path(args.workdir)
    stdout_path = Path(args.stdout_path)
    stderr_path = Path(args.stderr_path)
    meta_path = Path(args.meta_path)
    environment = str(os.environ.get("E2E_ENV_NAME") or "").strip().upper()

    payload = _read_payload(meta_path)
    payload.update(
        {
            "execution_id": args.execution_id,
            "status": "running",
            "worker_pid": os.getpid(),
            "pid": os.getpid(),
            "command": command,
            "workdir": str(workdir),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }
    )
    _write_payload(meta_path, payload)

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    exit_code = 1
    child_pid: int | None = None
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
            process = subprocess.Popen(
                command,
                cwd=str(workdir),
                env=os.environ.copy(),
                stdout=stdout_handle,
                stderr=stderr_handle,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
            child_pid = process.pid
            payload = _read_payload(meta_path)
            payload["child_pid"] = child_pid
            _write_payload(meta_path, payload)
            exit_code = process.wait()
    except Exception as exc:  # pragma: no cover - proteção operacional
        stderr_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        exit_code = 1

    stdout_payload = _decode_stdout_json(stdout_path)
    if exit_code == 0 and _payload_has_failure(stdout_payload):
        exit_code = 1
    summary_path, manifest_path = _infer_artifact_paths(stdout_payload, workdir, environment)

    final_payload = _read_payload(meta_path)
    final_payload.update(
        {
            "status": "passed" if exit_code == 0 else "failed",
            "exit_code": exit_code,
            "finished_at": datetime.now().isoformat(),
            "worker_pid": os.getpid(),
            "pid": os.getpid(),
            "child_pid": child_pid,
            "summary_path": summary_path,
            "manifest_path": manifest_path,
        }
    )
    _write_payload(meta_path, final_payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
