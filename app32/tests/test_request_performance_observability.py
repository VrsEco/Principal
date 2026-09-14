from pathlib import Path


def test_request_debug_io_is_opt_in_and_slow_requests_are_logged():
    root = Path(__file__).resolve().parents[1]
    config = (root / 'config.py').read_text(encoding='utf-8')
    app = (root / 'app.py').read_text(encoding='utf-8')

    assert 'REQUEST_DEBUG_LOG_ENABLED = env_flag("REQUEST_DEBUG_LOG_ENABLED", default=False)' in config
    assert 'SLOW_REQUEST_THRESHOLD_MS' in config
    assert 'if app.config.get("REQUEST_DEBUG_LOG_ENABLED", False):' in app
    assert 'g.request_started_at = time.perf_counter()' in app
    assert 'from flask import Flask, current_app, g, request, jsonify' in app
    assert '"slow_request method=%s path=%s status=%s duration_ms=%.1f"' in app
