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
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(
        [
            repo_root / "github_actions_deploy_key_fixed.txt",
            repo_root / "github_actions_deploy_key.txt",
        ]
    )
    return candidates


def resolve_private_key_path() -> Path:
    for path in _candidate_key_paths():
        if path.exists():
            return path
    searched = ", ".join(str(path) for path in _candidate_key_paths())
    raise FileNotFoundError(f"Nenhuma chave de deploy encontrada. Caminhos verificados: {searched}")


def load_private_key():
    key_text = resolve_private_key_path().read_text(encoding="utf-8").strip()
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
    raise ValueError("Não foi possível carregar a chave privada de deploy.")


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
