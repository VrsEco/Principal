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
import smtplib
import subprocess
import sys
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta
from email.message import EmailMessage
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
DEFAULT_ALERT_THROTTLE_HOURS = 12
STATUS_FILE = "last_status.json"
ALERT_STATE_FILE = ".last-alert.json"


class BackupRunError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_upload_inventory(upload_root: Path, destination: Path) -> tuple[list[dict[str, object]], int]:
    """Gera inventário verificável dos binários de uploads, sem alterar a fonte.

    O inventário é a referência de restauração: cada arquivo aponta para um
    objeto imutável identificado pelo seu SHA-256. Links simbólicos não entram
    no backup para impedir que a rotina saia da árvore autorizada de uploads.
    """
    if upload_root.is_symlink():
        raise BackupRunError(f"Diretório de uploads inválido ou ausente: {upload_root}")
    root = upload_root.resolve()
    if not root.is_dir():
        raise BackupRunError(f"Diretório de uploads inválido ou ausente: {upload_root}")

    files: list[dict[str, object]] = []
    total_bytes = 0
    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if root not in resolved.parents:
            raise BackupRunError(f"Arquivo de upload fora da raiz autorizada: {candidate}")
        size = candidate.stat().st_size
        files.append(
            {
                "relative_path": candidate.relative_to(root).as_posix(),
                "sha256": sha256_file(candidate),
                "size": size,
            }
        )
        total_bytes += size

    destination.write_text(
        json.dumps(
            {
                "schema": 1,
                "artifact": "uploads_inventory",
                "files_count": len(files),
                "total_bytes": total_bytes,
                "files": files,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return files, total_bytes


def build_upload_records(upload_root: Path, inventory_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Cria artefatos content-addressed; os caminhos ficam somente no inventário.

    O Google Drive impõe 124 bytes para a soma das ``appProperties``. Guardar
    caminhos de uploads nessas propriedades é desnecessário e falha para nomes
    longos; a restauração usa o inventário assinado da execução.
    """
    upload_files, upload_bytes = create_upload_inventory(upload_root, inventory_path)
    records: list[dict[str, object]] = [
        {
            "path": upload_root / str(item["relative_path"]),
            "type": "uploads",
            "sha256": str(item["sha256"]),
        }
        for item in upload_files
    ]
    records.append({"path": inventory_path, "type": "uploads_inventory"})
    return records, {"files_count": len(upload_files), "total_bytes": upload_bytes, "root": str(upload_root)}


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


def existing_artifacts(client: GoogleDriveBackupClient, artifacts: list[BackupArtifact]) -> dict[str, dict[str, object]]:
    """Consulta o Drive antes do envio para calcular somente bytes inéditos."""
    matches: dict[str, dict[str, object]] = {}
    for artifact in artifacts:
        existing = client.find_existing_artifact(artifact.object_key)
        if existing:
            matches[artifact.object_key] = existing
    return matches


def upload_artifacts(
    client: GoogleDriveBackupClient,
    artifacts: list[BackupArtifact],
    remote_folder: str,
    *,
    existing: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    parent_id = client.ensure_folder_path(["GV-Backups", *remote_folder.split("/")])
    results = []
    for artifact in artifacts:
        match = (existing or {}).get(artifact.object_key)
        if match is None:
            match = client.find_existing_artifact(artifact.object_key)
        results.append(
            {"status": "already_present", "name": artifact.path.name, "drive_file_id": match["id"]}
            if match else {"status": "uploaded", **client.upload_new_artifact(artifact, parent_id)}
        )
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(SCRIPT_DIR.parent.parent))
    parser.add_argument("--dotenv", default=str(SCRIPT_DIR.parent / ".env"))
    parser.add_argument("--staging-dir", default=os.getenv("GV_BACKUP_STAGING_DIR", DEFAULT_STAGING))
    parser.add_argument("--drive-env-file", default=os.getenv("GV_GOOGLE_DRIVE_ENV_FILE", DEFAULT_ENV_FILE))
    parser.add_argument(
        "--uploads-root",
        default=os.getenv("GV_BACKUP_UPLOADS_ROOT"),
        help="Raiz canônica dos anexos. Exige --include-uploads para ser usada.",
    )
    parser.add_argument(
        "--include-uploads",
        action="store_true",
        help="Inclui uploads como objetos incrementais. Não é habilitado pelo cron atual.",
    )
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
        uploads_inventory: dict[str, object] | None = None
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
        if args.include_uploads:
            upload_root = (Path(args.uploads_root) if args.uploads_root else repo / "uploads").resolve()
            inventory_path = run_dir / "uploads.inventory.json"
            upload_records, uploads_inventory = build_upload_records(upload_root, inventory_path)
            records.extend(upload_records)
        manifest = run_dir / "manifest.json"
        manifest.write_text(json.dumps({"schema": 3, "created_at": now.isoformat(), "git_commit": commit,
            "retention_tier": tier, "retain_until": expires.isoformat(),
            "artifacts": [{"name": x["path"].name, "type": x["type"], "sha256": x.get("sha256") or sha256_file(x["path"]), "size": x["path"].stat().st_size} for x in records],
            "code_reference": code_reference}, indent=2) + "\n", encoding="utf-8")
        if uploads_inventory:
            manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_payload["uploads_inventory"] = uploads_inventory
            manifest.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
        records.append({"path": manifest, "type": "manifest"})
        artifacts = [BackupArtifact(item["path"], item.get("sha256") or sha256_file(item["path"]), item["type"], item.get("extra_properties", {})) for item in records]
        existing = existing_artifacts(client, artifacts)
        required_bytes = sum(item.path.stat().st_size for item in artifacts if item.object_key not in existing)
        assert_drive_capacity(client.storage_quota(), required_bytes, minimum_free_bytes())
        results = upload_artifacts(client, artifacts, remote_folder, existing=existing)
        if code_reference:
            results.append({"status": "reused", "name": code_reference["name"], "type": "code", "git_commit": commit})
        elif (bundle := run_dir / "source.bundle").is_file():
            # O código validado já está no Drive. Mantê-lo em cada diretório
            # local multiplicaria 456 MB sem elevar a resiliência.
            bundle.unlink()
        removed = prune_local_staging(staging, now, exclude=run_dir)
    return {"ok": True, "mode": "upload", "run_dir": str(run_dir), "remote_folder": remote_folder,
            "retention_tier": tier, "retain_until": expires.isoformat(), "local_pruned_runs": removed, "results": results}


def _alert_setting(name: str, file_values: dict[str, str]) -> str:
    return os.getenv(name, file_values.get(name, "")).strip()


def load_alert_settings(drive_env_file: Path) -> dict[str, str]:
    """Le configuracao de alerta do ambiente ou do arquivo protegido do Drive."""
    try:
        file_values = load_env_file(drive_env_file)
    except Exception:  # arquivo ausente nao deve impedir o alerta por ambiente
        file_values = {}
    names = (
        "GV_BACKUP_ALERT_WEBHOOK_URL",
        "GV_BACKUP_ALERT_TO",
        "GV_BACKUP_ALERT_SMTP_HOST",
        "GV_BACKUP_ALERT_SMTP_PORT",
        "GV_BACKUP_ALERT_SMTP_USER",
        "GV_BACKUP_ALERT_SMTP_PASSWORD",
        "GV_BACKUP_ALERT_FROM",
        "GV_BACKUP_ALERT_THROTTLE_HOURS",
    )
    return {name: _alert_setting(name, file_values) for name in names}


def write_status(staging: Path, ok: bool, detail: str, now: datetime) -> None:
    """Registra o ultimo resultado para monitoramento externo (sem segredos)."""
    try:
        staging.mkdir(parents=True, exist_ok=True)
        path = staging / STATUS_FILE
        previous: dict[str, object] = {}
        if path.is_file():
            previous = json.loads(path.read_text(encoding="utf-8"))
        payload = {
            "ok": ok,
            "checked_at": now.isoformat(),
            "last_success_at": now.isoformat() if ok else previous.get("last_success_at"),
            "detail": detail[:500],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def should_send_alert(staging: Path, now: datetime, throttle_hours: int) -> bool:
    """Evita repetir o mesmo alerta a cada execucao do cron (5 por dia)."""
    path = staging / ALERT_STATE_FILE
    try:
        last = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["sent_at"])
    except Exception:
        return True
    return now - last >= timedelta(hours=throttle_hours)


def send_failure_alert(settings: dict[str, str], subject: str, body: str) -> list[str]:
    """Envia por webhook e/ou SMTP; devolve os canais que aceitaram a mensagem."""
    delivered: list[str] = []
    webhook = settings.get("GV_BACKUP_ALERT_WEBHOOK_URL", "")
    if webhook:
        request = urllib.request.Request(
            webhook,
            data=json.dumps({"text": f"{subject}\n{body}"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=15):  # noqa: S310 - URL vem de config protegida
            delivered.append("webhook")
    recipient = settings.get("GV_BACKUP_ALERT_TO", "")
    host = settings.get("GV_BACKUP_ALERT_SMTP_HOST", "")
    if recipient and host:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.get("GV_BACKUP_ALERT_FROM") or settings.get("GV_BACKUP_ALERT_SMTP_USER") or recipient
        message["To"] = recipient
        message.set_content(body)
        port = int(settings.get("GV_BACKUP_ALERT_SMTP_PORT") or 587)
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            user = settings.get("GV_BACKUP_ALERT_SMTP_USER")
            if user:
                server.login(user, settings.get("GV_BACKUP_ALERT_SMTP_PASSWORD", ""))
            server.send_message(message)
        delivered.append("smtp")
    return delivered


def notify_failure(args: argparse.Namespace, error: str) -> None:
    """Registra a falha e alerta com throttle. Nunca levanta excecao."""
    now = datetime.now(TZ)
    staging = Path(args.staging_dir)
    write_status(staging, False, error, now)
    try:
        settings = load_alert_settings(Path(args.drive_env_file))
        hours = int(settings.get("GV_BACKUP_ALERT_THROTTLE_HOURS") or DEFAULT_ALERT_THROTTLE_HOURS)
        if not should_send_alert(staging, now, hours):
            return
        last_ok = None
        status_path = staging / STATUS_FILE
        if status_path.is_file():
            last_ok = json.loads(status_path.read_text(encoding="utf-8")).get("last_success_at")
        body = (
            f"O backup externo do Gestao Versus falhou em {now.isoformat()}.\n"
            f"Erro: {error[:500]}\n"
            f"Ultimo sucesso registrado: {last_ok or 'desconhecido'}.\n"
            "Log: logs/app32/external_backup_cron.log no Configr."
        )
        delivered = send_failure_alert(settings, "[GV] Backup externo FALHOU", body)
        if delivered:
            (staging / ALERT_STATE_FILE).write_text(json.dumps({"sent_at": now.isoformat()}) + "\n", encoding="utf-8")
        else:
            print("Alerta nao enviado: nenhum canal GV_BACKUP_ALERT_* configurado.", file=sys.stderr)
    except Exception as exc:  # alerta nunca pode mascarar o erro original
        print(f"Falha ao enviar alerta: {exc}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
        if result.get("mode") == "upload":
            write_status(Path(args.staging_dir), True, "ok", datetime.now(TZ))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:  # inclui BackupDriveError (ex.: token OAuth expirado)
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        if args.upload and not args.dry_run:
            notify_failure(args, str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
