from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from utils.gcs_utils import get_gcs_config, upload_to_gcs


POP_VIDEO_MAX_DURATION_SECONDS = 150
POP_VIDEO_TARGET_BYTES_PER_MINUTE = 10_000_000
POP_VIDEO_MAX_OUTPUT_BYTES = 25_000_000
POP_VIDEO_MAX_SOURCE_FILE_BYTES = 100 * 1024 * 1024
POP_VIDEO_ALLOWED_EXTENSIONS = {".mp4", ".webm"}
POP_VIDEO_ALLOWED_MIME_PREFIXES = ("video/mp4", "video/webm")
POP_VIDEO_TRANSCODE_FPS = 15
POP_VIDEO_TRANSCODE_HEIGHT = 720
POP_VIDEO_TRANSCODE_AUDIO_BITRATE = "64k"
POP_VIDEO_TRANSCODE_AUDIO_BITRATE_BPS = 64_000
POP_VIDEO_TARGET_SAFETY_FACTOR = 0.92
POP_VIDEO_TRANSCODE_TIMEOUT_SECONDS = 120
POP_VIDEO_CHUNK_SIZE_BYTES = 8 * 1024 * 1024
POP_VIDEO_MAX_CHUNKS = 13
POP_VIDEO_CHUNK_TTL_SECONDS = 24 * 60 * 60


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
        raise ValueError("O vídeo do POP deve ter no máximo 2 minutos e 30 segundos.")

    if content_length and int(content_length) > POP_VIDEO_MAX_SOURCE_FILE_BYTES:
        raise ValueError("O arquivo original do vídeo excede o limite de 100 MB.")


def resolve_ffmpeg_binary() -> str | None:
    system_binary = shutil.which("ffmpeg")
    if system_binary:
        return system_binary
    try:
        import imageio_ffmpeg

        bundled_binary = imageio_ffmpeg.get_ffmpeg_exe()
        return bundled_binary if bundled_binary and os.path.exists(bundled_binary) else None
    except (ImportError, OSError):
        return None


def probe_video_duration_seconds(source_path: str, *, ffmpeg_bin: str | None = None) -> float | None:
    ffmpeg_cmd = ffmpeg_bin or resolve_ffmpeg_binary()
    if not ffmpeg_cmd:
        return None

    try:
        result = subprocess.run(
            [ffmpeg_cmd, "-hide_banner", "-i", source_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", result.stderr or "")
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)


def calculate_pop_video_target_bytes(duration_seconds: float) -> int:
    if duration_seconds <= 0:
        raise ValueError("Duração do vídeo inválida.")
    proportional_bytes = round(
        (float(duration_seconds) / 60.0) * POP_VIDEO_TARGET_BYTES_PER_MINUTE
    )
    return min(POP_VIDEO_MAX_OUTPUT_BYTES, max(1_000_000, proportional_bytes))


def calculate_pop_video_bitrate_bps(duration_seconds: float) -> int:
    target_bytes = calculate_pop_video_target_bytes(duration_seconds)
    safe_total_bps = int(
        (target_bytes * 8 / float(duration_seconds)) * POP_VIDEO_TARGET_SAFETY_FACTOR
    )
    return max(250_000, safe_total_bps - POP_VIDEO_TRANSCODE_AUDIO_BITRATE_BPS)


def transcode_pop_video_to_mp4(
    source_path: str,
    target_path: str,
    *,
    duration_seconds: float | None = None,
    ffmpeg_bin: str | None = None,
) -> bool:
    ffmpeg_cmd = ffmpeg_bin or resolve_ffmpeg_binary()
    if not ffmpeg_cmd:
        return False

    measured_duration = duration_seconds or probe_video_duration_seconds(
        source_path,
        ffmpeg_bin=ffmpeg_cmd,
    )
    if not measured_duration or measured_duration <= 0:
        return False

    video_bitrate = str(calculate_pop_video_bitrate_bps(measured_duration))
    target_bytes = calculate_pop_video_target_bytes(measured_duration)
    passlogfile = os.path.join(os.path.dirname(target_path), "ffmpeg-pass")
    common_video_args = [
        "-vf", f"scale=-2:'min({POP_VIDEO_TRANSCODE_HEIGHT},ih)'",
        "-r", str(POP_VIDEO_TRANSCODE_FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", video_bitrate,
        "-pix_fmt", "yuv420p",
    ]

    first_pass = [
        ffmpeg_cmd,
        "-y",
        "-i", source_path,
        "-map", "0:v:0",
        *common_video_args,
        "-pass", "1",
        "-passlogfile", passlogfile,
        "-an",
        "-f", "null",
        os.devnull,
    ]

    second_pass = [
        ffmpeg_cmd,
        "-y",
        "-i", source_path,
        "-map", "0:v:0",
        "-map", "0:a:0?",
        *common_video_args,
        "-pass", "2",
        "-passlogfile", passlogfile,
        "-c:a", "aac",
        "-b:a", POP_VIDEO_TRANSCODE_AUDIO_BITRATE,
        "-movflags", "+faststart",
        target_path,
    ]

    try:
        first_result = subprocess.run(
            first_pass,
            capture_output=True,
            text=True,
            check=False,
            timeout=POP_VIDEO_TRANSCODE_TIMEOUT_SECONDS,
        )
        if first_result.returncode != 0:
            return False
        second_result = subprocess.run(
            second_pass,
            capture_output=True,
            text=True,
            check=False,
            timeout=POP_VIDEO_TRANSCODE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if second_result.returncode != 0 or not os.path.exists(target_path):
        return False
    output_bytes = os.path.getsize(target_path)
    return 0 < output_bytes <= int(target_bytes * 1.03)


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

        ffmpeg_bin = resolve_ffmpeg_binary()
        if not ffmpeg_bin:
            raise ValueError("O otimizador de vídeo não está disponível no servidor.")

        duration_seconds = probe_video_duration_seconds(source_path, ffmpeg_bin=ffmpeg_bin)
        if not duration_seconds:
            raise ValueError("Não foi possível validar a duração do vídeo enviado.")
        validate_step_video_upload(
            file_storage,
            duration_seconds=int(duration_seconds + 0.999),
            content_length=os.path.getsize(source_path),
        )

        final_local_path = os.path.join(target_dir, final_name)
        transcoded = transcode_pop_video_to_mp4(
            source_path,
            transcoded_path,
            duration_seconds=duration_seconds,
            ffmpeg_bin=ffmpeg_bin,
        )

        if not transcoded:
            raise ValueError("Não foi possível otimizar o vídeo. Verifique o arquivo e tente novamente.")
        if get_gcs_config():
            with open(transcoded_path, "rb") as handle:
                gcs_path = upload_to_gcs(handle, final_name, subfolder=subfolder)
                if gcs_path:
                    return gcs_path
        shutil.copyfile(transcoded_path, final_local_path)
        return os.path.join(subfolder, final_name).replace("\\", "/") if subfolder else final_name


def _resolve_pop_video_chunk_root() -> Path:
    configured_root = current_app.config.get("POP_VIDEO_CHUNK_ROOT")
    return Path(configured_root or tempfile.gettempdir()) / "gv_pop_video_chunks"


def _cleanup_stale_pop_video_chunks(root: Path) -> None:
    if not root.exists():
        return
    cutoff = time.time() - POP_VIDEO_CHUNK_TTL_SECONDS
    for candidate in root.glob("*/*/*"):
        try:
            if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
                shutil.rmtree(candidate, ignore_errors=True)
        except OSError:
            continue


def save_pop_video_chunk(
    chunk_storage,
    *,
    company_id: int,
    step_id: int,
    upload_id: str,
    chunk_index: int,
    total_chunks: int,
    total_size: int,
    original_filename: str,
    original_mimetype: str,
    subfolder: str = "pop/video",
) -> str | None:
    """Persiste um bloco tenant-safe e otimiza quando todos os blocos chegaram."""
    try:
        normalized_upload_id = str(uuid.UUID(str(upload_id)))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("Identificador do upload inválido.")

    if not company_id or not step_id:
        raise ValueError("Contexto da empresa e do passo é obrigatório.")
    if total_chunks < 1 or total_chunks > POP_VIDEO_MAX_CHUNKS:
        raise ValueError("Quantidade de blocos do vídeo inválida.")
    if chunk_index < 0 or chunk_index >= total_chunks:
        raise ValueError("Índice do bloco do vídeo inválido.")
    if total_size <= 0 or total_size > POP_VIDEO_MAX_SOURCE_FILE_BYTES:
        raise ValueError("O arquivo original do vídeo excede o limite de 100 MB.")
    if not chunk_storage or not getattr(chunk_storage, "filename", None):
        raise ValueError("Bloco do vídeo não informado.")

    root = _resolve_pop_video_chunk_root()
    _cleanup_stale_pop_video_chunks(root)
    upload_dir = root / str(int(company_id)) / str(int(step_id)) / normalized_upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = upload_dir / f"{chunk_index:03d}.part"
    chunk_storage.save(chunk_path)
    if chunk_path.stat().st_size > POP_VIDEO_CHUNK_SIZE_BYTES:
        chunk_path.unlink(missing_ok=True)
        raise ValueError("Bloco do vídeo excede o limite de 8 MB.")

    if chunk_index < total_chunks - 1:
        return None

    expected_chunks = [upload_dir / f"{index:03d}.part" for index in range(total_chunks)]
    if not all(path.exists() for path in expected_chunks):
        raise ValueError("Upload incompleto. Envie novamente o vídeo.")

    safe_name = secure_filename(original_filename or "video.mp4") or "video.mp4"
    extension = Path(safe_name).suffix.lower() or ".mp4"
    assembled_path = upload_dir / f"assembled{extension}"
    try:
        with assembled_path.open("wb") as assembled:
            for path in expected_chunks:
                with path.open("rb") as chunk_handle:
                    shutil.copyfileobj(chunk_handle, assembled)
        if assembled_path.stat().st_size != total_size:
            raise ValueError("O tamanho final do upload não confere. Envie novamente o vídeo.")

        with assembled_path.open("rb") as assembled_handle:
            assembled_storage = FileStorage(
                stream=assembled_handle,
                filename=safe_name,
                content_type=original_mimetype or "video/mp4",
            )
            return save_pop_video(assembled_storage, subfolder=subfolder)
    finally:
        shutil.rmtree(upload_dir, ignore_errors=True)
