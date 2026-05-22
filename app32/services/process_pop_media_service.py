from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from utils.gcs_utils import get_gcs_config, upload_to_gcs


POP_VIDEO_MAX_DURATION_SECONDS = 120
POP_VIDEO_MAX_FILE_BYTES = 25 * 1024 * 1024
POP_VIDEO_ALLOWED_EXTENSIONS = {".mp4", ".webm"}
POP_VIDEO_ALLOWED_MIME_PREFIXES = ("video/mp4", "video/webm")
POP_VIDEO_TRANSCODE_FPS = 15
POP_VIDEO_TRANSCODE_HEIGHT = 720
POP_VIDEO_TRANSCODE_CRF = 30
POP_VIDEO_TRANSCODE_AUDIO_BITRATE = "64k"


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


def resolve_ffmpeg_binary() -> str | None:
    return shutil.which("ffmpeg")


def transcode_pop_video_to_mp4(source_path: str, target_path: str, *, ffmpeg_bin: str | None = None) -> bool:
    ffmpeg_cmd = ffmpeg_bin or resolve_ffmpeg_binary()
    if not ffmpeg_cmd:
        return False

    command = [
        ffmpeg_cmd,
        "-y",
        "-i", source_path,
        "-vf", f"scale=-2:'min({POP_VIDEO_TRANSCODE_HEIGHT},ih)'",
        "-r", str(POP_VIDEO_TRANSCODE_FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", str(POP_VIDEO_TRANSCODE_CRF),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", POP_VIDEO_TRANSCODE_AUDIO_BITRATE,
        target_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 0


def save_pop_video(file_storage, *, subfolder: str = "pop/video") -> str | None:
    if not file_storage or not getattr(file_storage, "filename", None):
        return None

    filename = secure_filename(str(file_storage.filename or "video.mp4"))
    stem = Path(filename).stem or "video"
    unique_base = f"{uuid.uuid4().hex}_{stem}"
    final_name = f"{unique_base}.mp4"

    upload_base = current_app.config.get("UPLOAD_FOLDER", "uploads")
    target_dir = os.path.join(upload_base, subfolder) if subfolder else upload_base
    os.makedirs(target_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="gv_pop_video_") as temp_dir:
        original_ext = Path(filename).suffix or ".mp4"
        source_path = os.path.join(temp_dir, f"source{original_ext}")
        transcoded_path = os.path.join(temp_dir, final_name)
        file_storage.save(source_path)

        final_local_path = os.path.join(target_dir, final_name)
        transcoded = transcode_pop_video_to_mp4(source_path, transcoded_path)

        if transcoded:
            if get_gcs_config():
                with open(transcoded_path, "rb") as handle:
                    gcs_path = upload_to_gcs(handle, final_name, subfolder=subfolder)
                    if gcs_path:
                        return gcs_path
            shutil.copyfile(transcoded_path, final_local_path)
            return os.path.join(subfolder, final_name).replace("\\", "/") if subfolder else final_name

        fallback_name = f"{unique_base}{original_ext}"
        fallback_local_path = os.path.join(target_dir, fallback_name)
        if get_gcs_config():
            with open(source_path, "rb") as handle:
                gcs_path = upload_to_gcs(handle, fallback_name, subfolder=subfolder)
                if gcs_path:
                    return gcs_path
        shutil.copyfile(source_path, fallback_local_path)
        return os.path.join(subfolder, fallback_name).replace("\\", "/") if subfolder else fallback_name
