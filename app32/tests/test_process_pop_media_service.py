import io
import os
import sys

import pytest
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.process_pop_media_service import (
    POP_VIDEO_MAX_DURATION_SECONDS,
    coerce_video_duration_seconds,
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
