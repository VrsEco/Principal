from __future__ import annotations

import os
from typing import Any


POP_VIDEO_MAX_DURATION_SECONDS = 120
POP_VIDEO_MAX_FILE_BYTES = 25 * 1024 * 1024
POP_VIDEO_ALLOWED_EXTENSIONS = {".mp4", ".webm"}
POP_VIDEO_ALLOWED_MIME_PREFIXES = ("video/mp4", "video/webm")


def coerce_video_duration_seconds(value: Any) -> int | None:
    if value in (None, "", False):
        return None
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        raise ValueError("Duração do vídeo inválida.")
    if seconds < 0:
        raise ValueError("Duração do vídeo inválida.")
    return seconds


def validate_step_video_upload(
    file_storage,
    *,
    duration_seconds: int | None = None,
    content_length: int | None = None,
) -> None:
    if not file_storage or not getattr(file_storage, "filename", None):
        raise ValueError("Vídeo não informado.")

    filename = str(file_storage.filename or "").strip().lower()
    extension = os.path.splitext(filename)[1]
    if extension not in POP_VIDEO_ALLOWED_EXTENSIONS:
        raise ValueError("Formato de vídeo não suportado. Envie MP4 ou WebM.")

    mime_type = str(getattr(file_storage, "mimetype", "") or "").strip().lower()
    if mime_type and not any(mime_type.startswith(prefix) for prefix in POP_VIDEO_ALLOWED_MIME_PREFIXES):
        raise ValueError("Tipo MIME de vídeo não suportado. Envie MP4 ou WebM.")

    if duration_seconds is not None and duration_seconds > POP_VIDEO_MAX_DURATION_SECONDS:
        raise ValueError("O vídeo do POP deve ter no máximo 120 segundos.")

    if content_length and int(content_length) > POP_VIDEO_MAX_FILE_BYTES:
        raise ValueError("O vídeo do POP excede o limite de 25 MB.")
