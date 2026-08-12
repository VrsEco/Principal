import io
import os
import sys
import uuid
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.process_pop_media_service import (
    POP_VIDEO_MAX_DURATION_SECONDS,
    POP_VIDEO_MAX_SOURCE_FILE_BYTES,
    calculate_pop_video_bitrate_bps,
    calculate_pop_video_target_bytes,
    coerce_video_duration_seconds,
    save_pop_video,
    save_pop_video_chunk,
    transcode_pop_video_to_mp4,
    validate_step_video_upload,
)


def _video_file(filename='passo.mp4', mime_type='video/mp4'):
    return FileStorage(stream=io.BytesIO(b'video-bytes'), filename=filename, content_type=mime_type)


def test_coerce_video_duration_seconds_accepts_blank():
    assert coerce_video_duration_seconds(None) is None
    assert coerce_video_duration_seconds('') is None


def test_coerce_video_duration_seconds_parses_numeric_string():
    assert coerce_video_duration_seconds('118') == 118
    assert coerce_video_duration_seconds('118.9') == 118


def test_validate_step_video_upload_accepts_short_mp4():
    validate_step_video_upload(
        _video_file(),
        duration_seconds=POP_VIDEO_MAX_DURATION_SECONDS,
        content_length=1024,
    )


def test_validate_step_video_upload_rejects_long_video():
    with pytest.raises(ValueError, match='2 minutos e 30 segundos'):
        validate_step_video_upload(_video_file(), duration_seconds=151)


def test_validate_step_video_upload_rejects_unsupported_extension():
    with pytest.raises(ValueError, match='MP4 ou WebM'):
        validate_step_video_upload(_video_file(filename='passo.avi', mime_type='video/avi'))


def test_validate_step_video_upload_rejects_source_above_100_mb():
    with pytest.raises(ValueError, match='100 MB'):
        validate_step_video_upload(
            _video_file(),
            duration_seconds=60,
            content_length=POP_VIDEO_MAX_SOURCE_FILE_BYTES + 1,
        )


def test_target_size_is_ten_mb_per_minute_with_25_mb_cap():
    assert calculate_pop_video_target_bytes(60) == 10_000_000
    assert calculate_pop_video_target_bytes(150) == 25_000_000
    assert calculate_pop_video_bitrate_bps(60) > 1_000_000


def test_transcode_pop_video_to_mp4_returns_false_when_ffmpeg_missing(tmp_path):
    source = tmp_path / 'source.webm'
    target = tmp_path / 'target.mp4'
    source.write_bytes(b'video')

    assert transcode_pop_video_to_mp4(str(source), str(target), ffmpeg_bin=None) is False


def test_save_pop_video_rejects_when_ffmpeg_unavailable(tmp_path, monkeypatch):
    from flask import Flask

    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = str(tmp_path)

    monkeypatch.setattr('services.process_pop_media_service.resolve_ffmpeg_binary', lambda: None)
    monkeypatch.setattr('services.process_pop_media_service.get_gcs_config', lambda: None)

    with app.app_context(), pytest.raises(ValueError, match='otimizador de vídeo'):
        save_pop_video(_video_file(filename='passo.webm', mime_type='video/webm'))


def test_save_pop_video_uses_transcoded_mp4_when_ffmpeg_succeeds(tmp_path, monkeypatch):
    from flask import Flask

    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = str(tmp_path)

    monkeypatch.setattr('services.process_pop_media_service.get_gcs_config', lambda: None)
    monkeypatch.setattr('services.process_pop_media_service.resolve_ffmpeg_binary', lambda: 'ffmpeg')
    monkeypatch.setattr('services.process_pop_media_service.probe_video_duration_seconds', lambda *args, **kwargs: 60.0)

    def _fake_transcode(source_path, target_path, *, duration_seconds=None, ffmpeg_bin=None):
        Path(target_path).write_bytes(b'compressed-video')
        return True

    monkeypatch.setattr('services.process_pop_media_service.transcode_pop_video_to_mp4', _fake_transcode)

    with app.app_context():
        stored_path = save_pop_video(_video_file(filename='passo.webm', mime_type='video/webm'))

    assert stored_path is not None
    assert stored_path.startswith('pop/video/')
    assert stored_path.endswith('.mp4')
    assert (tmp_path / stored_path).exists()


def test_chunked_upload_reassembles_inside_tenant_and_optimizes(tmp_path, monkeypatch):
    from flask import Flask

    app = Flask(__name__)
    app.config['POP_VIDEO_CHUNK_ROOT'] = str(tmp_path)
    upload_id = str(uuid.uuid4())
    assembled_payloads = []

    def _fake_save(file_storage, *, subfolder='pop/video'):
        assembled_payloads.append(file_storage.stream.read())
        return f'{subfolder}/optimized.mp4'

    monkeypatch.setattr('services.process_pop_media_service.save_pop_video', _fake_save)

    with app.app_context():
        first_result = save_pop_video_chunk(
            _video_file(filename='chunk-0.part', mime_type='application/octet-stream'),
            company_id=10,
            step_id=87,
            upload_id=upload_id,
            chunk_index=0,
            total_chunks=2,
            total_size=len(b'video-bytes') * 2,
            original_filename='passo.mp4',
            original_mimetype='video/mp4',
        )
        final_result = save_pop_video_chunk(
            _video_file(filename='chunk-1.part', mime_type='application/octet-stream'),
            company_id=10,
            step_id=87,
            upload_id=upload_id,
            chunk_index=1,
            total_chunks=2,
            total_size=len(b'video-bytes') * 2,
            original_filename='passo.mp4',
            original_mimetype='video/mp4',
        )

    assert first_result is None
    assert final_result == 'pop/video/optimized.mp4'
    assert assembled_payloads == [b'video-bytesvideo-bytes']
