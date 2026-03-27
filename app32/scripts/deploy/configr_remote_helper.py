from __future__ import annotations

import io
import os
from pathlib import Path

import paramiko

HOST = "69.164.205.75"
PORT = 22122
USER = "app"
BASE_DIR = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud"
WWW_DIR = f"{BASE_DIR}/www"
APP_DIR = f"{WWW_DIR}/app32"
DEPLOY_SCRIPT = f"{APP_DIR}/scripts/deploy_configr.sh"


def _candidate_key_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[3]
    env_path = os.getenv("GV_DEPLOY_KEY_PATH")
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    app_dir = repo_root / "app32"
    if app_dir.exists():
        candidates.append(app_dir / "deploy_key_SECRETA.txt")
    if repo_root.name == "www":
        candidates.append(repo_root.parent / "etc" / "secure" / "github_actions_deploy_key.txt")
    candidates.extend(
        [
            repo_root / "github_actions_deploy_key_fixed.txt",
            repo_root / "github_actions_deploy_key.txt",
        ]
    )
    return candidates


def resolve_private_key_path() -> Path:
    for path in _candidate_key_paths():
        if path.exists() and path.is_file():
            return path
    searched = ", ".join(str(path) for path in _candidate_key_paths())
    raise FileNotFoundError(f"Nenhuma chave de deploy encontrada. Caminhos verificados: {searched}")


def load_private_key():
    checked_paths: list[str] = []
    for path in _candidate_key_paths():
        checked_paths.append(str(path))
        try:
            key_bytes = path.read_bytes()
        except (FileNotFoundError, PermissionError, OSError):
            continue
        key_text = None
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252"):
            try:
                candidate = key_bytes.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
            if candidate:
                key_text = candidate
                break
        if not key_text:
            continue
        loaders = (
            paramiko.Ed25519Key.from_private_key,
            paramiko.RSAKey.from_private_key,
            paramiko.ECDSAKey.from_private_key,
        )
        for loader in loaders:
            try:
                return loader(io.StringIO(key_text))
            except Exception:
                continue
    searched = ", ".join(checked_paths)
    raise ValueError(f"Não foi possível carregar a chave privada de deploy. Caminhos verificados: {searched}")


def connect_ssh() -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        HOST,
        port=PORT,
        username=USER,
        pkey=load_private_key(),
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
    )
    return ssh


def run_command(ssh: paramiko.SSHClient, command: str, *, get_pty: bool = False) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=get_pty)
    out = stdout.read().decode("utf-8", "ignore")
    err = stderr.read().decode("utf-8", "ignore")
    code = stdout.channel.recv_exit_status()
    return code, out, err
