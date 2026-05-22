import io
import os
import sys
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.process_pop_media_service import (
    POP_VIDEO_MAX_DURATION_SECONDS,
    coerce_video_duration_seconds,
    save_pop_video,
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
    with pytest.raises(ValueError, match='máximo 120 segundos'):
        validate_step_video_upload(_video_file(), duration_seconds=121)


def test_validate_step_video_upload_rejects_unsupported_extension():
    with pytest.raises(ValueError, match='MP4 ou WebM'):
        validate_step_video_upload(_video_file(filename='passo.avi', mime_type='video/avi'))


def test_transcode_pop_video_to_mp4_returns_false_when_ffmpeg_missing(tmp_path):
    source = tmp_path / 'source.webm'
    target = tmp_path / 'target.mp4'
    source.write_bytes(b'video')

    assert transcode_pop_video_to_mp4(str(source), str(target), ffmpeg_bin=None) is False


def test_save_pop_video_falls_back_to_original_when_ffmpeg_unavailable(tmp_path, monkeypatch):
    from flask import Flask

    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = str(tmp_path)

    monkeypatch.setattr('services.process_pop_media_service.resolve_ffmpeg_binary', lambda: None)
    monkeypatch.setattr('services.process_pop_media_service.get_gcs_config', lambda: None)

    with app.app_context():
        stored_path = save_pop_video(_video_file(filename='passo.webm', mime_type='video/webm'))

    assert stored_path is not None
    assert stored_path.startswith('pop/video/')
    assert stored_path.endswith('.webm')
    assert (tmp_path / stored_path).exists()


def test_save_pop_video_uses_transcoded_mp4_when_ffmpeg_succeeds(tmp_path, monkeypatch):
    from flask import Flask

    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = str(tmp_path)

    monkeypatch.setattr('services.process_pop_media_service.get_gcs_config', lambda: None)

    def _fake_transcode(source_path, target_path, *, ffmpeg_bin=None):
        Path(target_path).write_bytes(b'compressed-video')
        return True

    monkeypatch.setattr('services.process_pop_media_service.transcode_pop_video_to_mp4', _fake_transcode)

    with app.app_context():
        stored_path = save_pop_video(_video_file(filename='passo.webm', mime_type='video/webm'))

    assert stored_path is not None
    assert stored_path.startswith('pop/video/')
    assert stored_path.endswith('.mp4')
    assert (tmp_path / stored_path).exists()
