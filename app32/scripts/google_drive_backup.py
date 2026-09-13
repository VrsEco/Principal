#!/usr/bin/env python3
"""Envio *append-only* de artefatos de backup para o Google Drive.

Esta ferramenta e executada no Configr. Ela deliberadamente nao implementa
nenhuma chamada de exclusao ou de sobrescrita remota: cada artefato recebe um
nome imutavel e uma segunda execucao do mesmo arquivo somente o ignora.

Os segredos devem ficar fora do Git, por exemplo em
``/home/app/.config/gv-backup/google_oauth.env`` (modo 0600). O token de
renovacao e provisionado separadamente depois do consentimento interativo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import requests


DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
DEFAULT_ENV_FILE = "/home/app/.config/gv-backup/google_oauth.env"


class BackupDriveError(RuntimeError):
    """Erro recuperavel da integracao com o Google Drive."""


def load_env_file(path: Path) -> dict[str, str]:
    """Le um arquivo ``KEY=VALUE`` sem imprimir valores sensiveis."""
    if not path.is_file():
        raise BackupDriveError(f"Arquivo de configuracao ausente: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_setting(name: str, file_values: dict[str, str]) -> str:
    value = os.getenv(name, file_values.get(name, "")).strip()
    if not value:
        raise BackupDriveError(f"Configuracao obrigatoria ausente: {name}")
    return value


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@dataclass(frozen=True)
class BackupArtifact:
    path: Path
    sha256: str
    artifact_type: str
    extra_properties: dict[str, str] = field(default_factory=dict)

    @property
    def object_key(self) -> str:
        return f"{self.artifact_type}:{self.sha256}"


class GoogleDriveBackupClient:
    """Cliente minimo da Drive API sem operacoes destrutivas."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token: str | None = None
        self.session = requests.Session()

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self._access_token()}"
        response = self.session.request(method, url, headers=headers, timeout=120, **kwargs)
        if response.status_code >= 400:
            detail = response.text[:600]
            raise BackupDriveError(f"Google Drive respondeu HTTP {response.status_code}: {detail}")
        return response

    def _access_token(self) -> str:
        if self.access_token:
            return self.access_token
        response = self.session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise BackupDriveError(
                f"Nao foi possivel renovar token OAuth (HTTP {response.status_code})."
            )
        token = response.json().get("access_token")
        if not token:
            raise BackupDriveError("Resposta OAuth sem access_token.")
        self.access_token = token
        return token

    def _list(self, query: str) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            f"{DRIVE_API}/files",
            params={
                "q": query,
                "spaces": "drive",
                "fields": "files(id,name,mimeType,appProperties,size,createdTime)",
                "pageSize": 100,
            },
        )
        return response.json().get("files", [])

    def ensure_folder_path(self, parts: Iterable[str]) -> str:
        """Cria somente as pastas faltantes e retorna a pasta final."""
        parent_id = "root"
        for part in parts:
            clean_part = part.strip().strip("/")
            if not clean_part:
                continue
            query = (
                f"name = '{escape_drive_query(clean_part)}' and "
                f"mimeType = '{FOLDER_MIME_TYPE}' and "
                f"'{parent_id}' in parents and trashed = false"
            )
            existing = self._list(query)
            if existing:
                parent_id = existing[0]["id"]
                continue
            response = self._request(
                "POST",
                f"{DRIVE_API}/files",
                json={"name": clean_part, "mimeType": FOLDER_MIME_TYPE, "parents": [parent_id]},
            )
            parent_id = response.json()["id"]
        return parent_id

    def find_existing_artifact(self, object_key: str) -> dict[str, Any] | None:
        query = (
            f"appProperties has {{ key='gv_backup_object_key' and "
            f"value='{escape_drive_query(object_key)}' }} and trashed = false"
        )
        matches = self._list(query)
        return matches[0] if matches else None

    def find_existing_code_commit(self, commit: str) -> dict[str, Any] | None:
        """Localiza um bundle de código já associado ao commit informado.

        O índice fica no próprio artefato e permite pular a geração de um
        bundle completo nas execuções seguintes. A consulta é somente leitura.
        """
        query = (
            "appProperties has { key='gv_backup_git_commit' and "
            f"value='{escape_drive_query(commit)}' }} and trashed = false"
        )
        matches = self._list(query)
        return matches[0] if matches else None

    def storage_quota(self) -> dict[str, int | None]:
        """Lê a quota da conta, sem alterar arquivos do Drive."""
        response = self._request("GET", f"{DRIVE_API}/about", params={"fields": "storageQuota(limit,usage)"})
        raw = response.json().get("storageQuota", {})

        def as_int(value: Any) -> int | None:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        return {"limit": as_int(raw.get("limit")), "usage": as_int(raw.get("usage"))}

    def upload_new_artifact(self, artifact: BackupArtifact, parent_id: str) -> dict[str, Any]:
        """Faz upload resumivel de um novo arquivo, sem atualizar objetos existentes."""
        content_type = mimetypes.guess_type(artifact.path.name)[0] or "application/octet-stream"
        metadata = {
            "name": artifact.path.name,
            "parents": [parent_id],
            "appProperties": {
                "gv_backup_object_key": artifact.object_key,
                "gv_backup_sha256": artifact.sha256,
                "gv_backup_type": artifact.artifact_type,
                **artifact.extra_properties,
            },
        }
        session_response = self._request(
            "POST",
            f"{DRIVE_UPLOAD_API}/files",
            params={"uploadType": "resumable", "fields": "id,name,size,createdTime"},
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": content_type,
                "X-Upload-Content-Length": str(artifact.path.stat().st_size),
            },
            data=json.dumps(metadata),
        )
        upload_url = session_response.headers.get("Location")
        if not upload_url:
            raise BackupDriveError("Google Drive nao retornou URL de upload resumivel.")

        with artifact.path.open("rb") as source:
            response = self._request(
                "PUT",
                upload_url,
                headers={"Content-Type": content_type},
                data=source,
            )
        return response.json()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=os.getenv("GV_GOOGLE_DRIVE_ENV_FILE", DEFAULT_ENV_FILE),
        help="Arquivo seguro com credenciais OAuth (padrao: %(default)s).",
    )
    parser.add_argument(
        "--remote-folder",
        required=True,
        help="Caminho relativo abaixo da raiz GV-Backups no Google Drive.",
    )
    parser.add_argument(
        "--artifact-type",
        required=True,
        choices=("database", "code", "uploads", "manifest"),
    )
    parser.add_argument("--source", action="append", required=True, help="Arquivo local para envio.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida entradas e hashes; nao acessa nem altera o Google Drive.",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    source_paths = [Path(raw).expanduser().resolve() for raw in args.source]
    for path in source_paths:
        if not path.is_file():
            raise BackupDriveError(f"Artefato inexistente ou nao regular: {path}")

    artifacts = [
        BackupArtifact(path=path, sha256=sha256_file(path), artifact_type=args.artifact_type)
        for path in source_paths
    ]
    if args.dry_run:
        return [
            {
                "status": "validated",
                "name": artifact.path.name,
                "size": artifact.path.stat().st_size,
                "sha256": artifact.sha256,
                "remote_folder": args.remote_folder,
            }
            for artifact in artifacts
        ]

    settings = load_env_file(Path(args.env_file))
    client = GoogleDriveBackupClient(
        client_id=get_setting("GV_GOOGLE_DRIVE_CLIENT_ID", settings),
        client_secret=get_setting("GV_GOOGLE_DRIVE_CLIENT_SECRET", settings),
        refresh_token=get_setting("GV_GOOGLE_DRIVE_REFRESH_TOKEN", settings),
    )
    remote_parts = ["GV-Backups", *args.remote_folder.split("/")]
    parent_id = client.ensure_folder_path(remote_parts)
    results: list[dict[str, Any]] = []
    for artifact in artifacts:
        existing = client.find_existing_artifact(artifact.object_key)
        if existing:
            results.append(
                {
                    "status": "already_present",
                    "name": artifact.path.name,
                    "sha256": artifact.sha256,
                    "drive_file_id": existing["id"],
                }
            )
            continue
        uploaded = client.upload_new_artifact(artifact, parent_id)
        results.append(
            {
                "status": "uploaded",
                "name": artifact.path.name,
                "sha256": artifact.sha256,
                "drive_file_id": uploaded["id"],
                "size": uploaded.get("size"),
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        print(json.dumps({"ok": True, "results": run(args)}, ensure_ascii=False))
        return 0
    except BackupDriveError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
