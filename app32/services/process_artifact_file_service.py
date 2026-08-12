from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services.process_artifact_service import ProcessArtifactValidationError, get_artifact_execution


MAX_DOCUMENT_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_FILE_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv",
    ".doc", ".docx", ".xls", ".xlsx",
}


def _private_execution_dir(company_id: int, process_instance_id: int, artifact_execution_id: int) -> Path:
    return (
        Path(current_app.instance_path)
        / "private_process_artifacts"
        / str(int(company_id))
        / str(int(process_instance_id))
        / str(int(artifact_execution_id))
    )


def save_artifact_execution_file(
    company_id: int,
    artifact_execution_id: int,
    file_storage: FileStorage,
) -> dict[str, Any]:
    execution = get_artifact_execution(company_id, artifact_execution_id)
    if execution.status in {"completed", "skipped"}:
        raise ProcessArtifactValidationError("Documento concluído é somente leitura e não aceita novos arquivos.")
    original_name = secure_filename(str(getattr(file_storage, "filename", "") or ""))
    if not original_name:
        raise ProcessArtifactValidationError("Selecione um arquivo válido.")
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_FILE_EXTENSIONS:
        raise ProcessArtifactValidationError("Tipo de arquivo não permitido.")

    stream = file_storage.stream
    current_position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(current_position)
    if size <= 0:
        raise ProcessArtifactValidationError("O arquivo está vazio.")
    if size > MAX_DOCUMENT_FILE_BYTES:
        raise ProcessArtifactValidationError("O arquivo excede o limite de 10 MB.")

    file_key = f"{uuid4().hex}{extension}"
    target_dir = _private_execution_dir(company_id, execution.process_instance_id, execution.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    file_storage.save(target_dir / file_key)
    return {
        "file_key": file_key,
        "name": original_name,
        "size": int(size),
        "mime_type": str(getattr(file_storage, "mimetype", None) or "application/octet-stream"),
        "download_url": f"/api/process-artifact-executions/{execution.id}/files/{file_key}?company_id={company_id}",
    }


def _contains_file_key(value: Any, file_key: str) -> bool:
    if isinstance(value, dict):
        if value.get("file_key") == file_key:
            return True
        return any(_contains_file_key(item, file_key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_file_key(item, file_key) for item in value)
    return False


def resolve_artifact_execution_file(company_id: int, artifact_execution_id: int, file_key: str) -> tuple[Path, str, str]:
    execution = get_artifact_execution(company_id, artifact_execution_id)
    safe_key = secure_filename(str(file_key or ""))
    if safe_key != file_key or not safe_key:
        raise ProcessArtifactValidationError("Arquivo inválido.")
    stored_payload = {
        "output_json": execution.output_json or {},
        "evidence_json": execution.evidence_json or {},
    }
    if not _contains_file_key(stored_payload, safe_key):
        raise ProcessArtifactValidationError("Arquivo não vinculado a esta execução.")
    path = _private_execution_dir(company_id, execution.process_instance_id, execution.id) / safe_key
    if not path.is_file():
        raise ProcessArtifactValidationError("Arquivo não encontrado.")

    metadata = None
    stack = [stored_payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if current.get("file_key") == safe_key:
                metadata = current
                break
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return path, str((metadata or {}).get("name") or safe_key), str((metadata or {}).get("mime_type") or "application/octet-stream")
