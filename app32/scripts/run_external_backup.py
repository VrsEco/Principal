#!/usr/bin/env python3
"""Orquestra backup externo de banco e código sem exclusão remota.

Por segurança, upload real exige ``--upload``. Sem essa flag, ``--dry-run``
apenas valida o plano e nunca acessa o banco, o Git ou o Google Drive.
"""
from __future__ import annotations

import argparse
try:
    import fcntl
except ImportError:  # Windows local test environment
    fcntl = None
import hashlib
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from google_drive_backup import (  # noqa: E402
    BackupArtifact,
    GoogleDriveBackupClient,
    get_setting,
    load_env_file,
)

TZ = ZoneInfo("America/Bahia")
DEFAULT_STAGING = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/backups/gv-external"
DEFAULT_ENV_FILE = "/home/app/.config/gv-backup/google_oauth.env"
DEFAULT_MIN_FREE_BYTES = 1024 * 1024 * 1024


class BackupRunError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_postgres_url(value: str) -> tuple[str, str, str, str, str]:
    parsed = urlparse(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.path.strip("/"):
        raise BackupRunError("DATABASE_URL deve apontar para PostgreSQL.")
    return (
        parsed.hostname or "localhost",
        str(parsed.port or 5432),
        unquote(parsed.username or "postgres"),
        unquote(parsed.password or ""),
        parsed.path.lstrip("/"),
    )


@contextmanager
def exclusive_lock(lock_file: Path):
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("w") as lock:
        if fcntl is None:
            yield
            return
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BackupRunError("Já existe uma execução de backup em andamento.") from exc
        yield


def command_or_error(command: list[str], *, env: dict[str, str], label: str) -> None:
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-800:]
        raise BackupRunError(f"{label} falhou (exit {result.returncode}): {detail}")


def create_database_dump(destination: Path, database_url: str) -> None:
    host, port, user, password, database = parse_postgres_url(database_url)
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    command_or_error(
        ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", database,
         "--format=custom", "--no-owner", "--no-acl", "--file", str(destination)],
        env=env,
        label="pg_dump",
    )
    command_or_error(["pg_restore", "--list", str(destination)], env=env, label="pg_restore --list")


def create_code_bundle(repo: Path, destination: Path) -> str:
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    command_or_error(["git", "-C", str(repo), "bundle", "create", str(destination), "--all"], env=os.environ.copy(), label="git bundle")
    command_or_error(["git", "-C", str(repo), "bundle", "verify", str(destination)], env=os.environ.copy(), label="git bundle verify")
    return commit


def current_commit(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def retention_until(now: datetime, tier: str) -> datetime:
    """Retorna data de corte sem depender de bibliotecas externas."""
    if tier == "monthly":
        # O marco mensal do dia 1 é preservado até completar 180 dias.
        return now + timedelta(days=180)
    return now + timedelta(days=90 if tier == "daily" else 30)


def retention_metadata(now: datetime) -> tuple[str, datetime]:
    if now.hour == 3 and now.day == 1:
        tier = "monthly"
    elif now.hour == 3:
        tier = "daily"
    else:
        tier = "intraday"
    return tier, retention_until(now, tier)


def minimum_free_bytes() -> int:
    raw = os.getenv("GV_GOOGLE_DRIVE_MIN_FREE_BYTES", str(DEFAULT_MIN_FREE_BYTES))
    try:
        value = int(raw)
    except ValueError as exc:
        raise BackupRunError("GV_GOOGLE_DRIVE_MIN_FREE_BYTES deve ser inteiro.") from exc
    if value < 0:
        raise BackupRunError("GV_GOOGLE_DRIVE_MIN_FREE_BYTES não pode ser negativo.")
    return value


def assert_drive_capacity(quota: dict[str, int | None], required_bytes: int, reserve_bytes: int) -> None:
    limit, usage = quota.get("limit"), quota.get("usage")
    if limit is None or usage is None:
        raise BackupRunError("Não foi possível obter a quota do Google Drive; upload bloqueado por segurança.")
    available = limit - usage
    if available < required_bytes + reserve_bytes:
        raise BackupRunError(
            "Espaço insuficiente no Google Drive para este backup e a reserva de segurança "
            f"({available} disponíveis; {required_bytes + reserve_bytes} necessários)."
        )


def prune_local_staging(staging: Path, now: datetime, *, exclude: Path) -> list[str]:
    """Remove somente cópias locais vencidas que já possuem manifesto GFS.

    Nunca toca no Google Drive e ignora diretórios legados sem metadados de
    retenção, mantendo comportamento conservador em caso de parsing falho.
    """
    removed: list[str] = []
    if not staging.is_dir():
        return removed
    for candidate in staging.iterdir():
        if not candidate.is_dir() or candidate == exclude:
            continue
        manifest = candidate / "manifest.json"
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            expires = datetime.fromisoformat(payload["retain_until"])
            if expires.tzinfo is None or expires > now:
                continue
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        shutil.rmtree(candidate)
        removed.append(candidate.name)
    return removed


def create_drive_client(env_file: Path) -> GoogleDriveBackupClient:
    values = load_env_file(env_file)
    return GoogleDriveBackupClient(
        get_setting("GV_GOOGLE_DRIVE_CLIENT_ID", values),
        get_setting("GV_GOOGLE_DRIVE_CLIENT_SECRET", values),
        get_setting("GV_GOOGLE_DRIVE_REFRESH_TOKEN", values),
    )


def upload_artifacts(client: GoogleDriveBackupClient, artifacts: list[BackupArtifact], remote_folder: str) -> list[dict[str, object]]:
    parent_id = client.ensure_folder_path(["GV-Backups", *remote_folder.split("/")])
    results = []
    for artifact in artifacts:
        existing = client.find_existing_artifact(artifact.object_key)
        results.append(
            {"status": "already_present", "name": artifact.path.name, "drive_file_id": existing["id"]}
            if existing else {"status": "uploaded", **client.upload_new_artifact(artifact, parent_id)}
        )
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(SCRIPT_DIR.parent.parent))
    parser.add_argument("--dotenv", default=str(SCRIPT_DIR.parent / ".env"))
    parser.add_argument("--staging-dir", default=os.getenv("GV_BACKUP_STAGING_DIR", DEFAULT_STAGING))
    parser.add_argument("--drive-env-file", default=os.getenv("GV_GOOGLE_DRIVE_ENV_FILE", DEFAULT_ENV_FILE))
    parser.add_argument("--upload", action="store_true", help="Permite envio externo ao Google Drive.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o plano sem criar ou enviar artefatos.")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, object]:
    repo = Path(args.repo).resolve()
    staging = Path(args.staging_dir).resolve()
    now = datetime.now(TZ)
    run_id = now.strftime("%Y%m%dT%H%M%S%z")
    tier, expires = retention_metadata(now)
    remote_folder = f"gfs/{tier}/{now:%Y/%m/%d}/{run_id}"
    if args.dry_run:
        return {"ok": True, "mode": "dry-run", "remote_folder": remote_folder, "upload_enabled": False}
    if not args.upload:
        raise BackupRunError("Recusado: use --upload somente na rotina aprovada.")
    dotenv = Path(args.dotenv)
    if not dotenv.is_absolute():
        dotenv = repo / dotenv
    load_dotenv(dotenv_path=dotenv, override=False)
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise BackupRunError("DATABASE_URL ausente no ambiente protegido.")
    with exclusive_lock(staging / ".external-backup.lock"):
        run_dir = staging / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        os.chmod(run_dir, 0o700)
        client = create_drive_client(Path(args.drive_env_file))
        dump = run_dir / "database.dump"
        create_database_dump(dump, database_url)
        commit = current_commit(repo)
        existing_code = client.find_existing_code_commit(commit)
        records = [
            {"path": dump, "type": "database"},
        ]
        code_reference: dict[str, object] | None = None
        if existing_code:
            props = existing_code.get("appProperties", {})
            code_reference = {
                "drive_file_id": existing_code["id"],
                "name": existing_code["name"],
                "sha256": props.get("gv_backup_sha256"),
                "size": int(existing_code.get("size") or 0),
                "git_commit": commit,
            }
        else:
            bundle = run_dir / "source.bundle"
            create_code_bundle(repo, bundle)
            records.append({"path": bundle, "type": "code", "extra_properties": {"gv_backup_git_commit": commit}})
        manifest = run_dir / "manifest.json"
        manifest.write_text(json.dumps({"schema": 2, "created_at": now.isoformat(), "git_commit": commit,
            "retention_tier": tier, "retain_until": expires.isoformat(),
            "artifacts": [{"name": x["path"].name, "type": x["type"], "sha256": sha256_file(x["path"]), "size": x["path"].stat().st_size} for x in records],
            "code_reference": code_reference}, indent=2) + "\n", encoding="utf-8")
        records.append({"path": manifest, "type": "manifest"})
        artifacts = [BackupArtifact(item["path"], sha256_file(item["path"]), item["type"], item.get("extra_properties", {})) for item in records]
        assert_drive_capacity(client.storage_quota(), sum(item.path.stat().st_size for item in artifacts), minimum_free_bytes())
        results = upload_artifacts(client, artifacts, remote_folder)
        if code_reference:
            results.append({"status": "reused", "name": code_reference["name"], "type": "code", "git_commit": commit})
        elif (bundle := run_dir / "source.bundle").is_file():
            # O código validado já está no Drive. Mantê-lo em cada diretório
            # local multiplicaria 456 MB sem elevar a resiliência.
            bundle.unlink()
        removed = prune_local_staging(staging, now, exclude=run_dir)
    return {"ok": True, "mode": "upload", "run_dir": str(run_dir), "remote_folder": remote_folder,
            "retention_tier": tier, "retain_until": expires.isoformat(), "local_pruned_runs": removed, "results": results}


def main() -> int:
    try:
        print(json.dumps(run(parse_args()), ensure_ascii=False))
        return 0
    except BackupRunError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
