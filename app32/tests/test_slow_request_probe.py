import importlib.util
import json
import logging
from pathlib import Path
import threading
import time
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "slow_request_probe", Path(__file__).resolve().parents[1] / "utils/slow_request_probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_disabled_does_not_wrap():
    app = Mock(config={})
    original = app.wsgi_app
    probe.install_slow_request_probe(app)
    assert app.wsgi_app is original


def test_fast_response_and_exception_cleanup():
    logger = Mock()
    middleware = probe.SlowRequestProbe(lambda e, s: [b"ok"], logger, seconds=1)
    assert list(middleware({}, Mock())) == [b"ok"]
    def fail(e, s):
        raise RuntimeError("failure")
    middleware.app = fail
    with pytest.raises(RuntimeError):
        middleware({}, Mock())
    assert middleware.slots._value == 16
    logger.warning.assert_not_called()


def test_real_timer_captures_blocked_thread_without_secrets():
    records = []
    captured = threading.Event()
    def log(fmt, value):
        records.append(json.loads(value))
        captured.set()
    logger = Mock()
    logger.warning.side_effect = log
    def blocked(environ, start_response):
        private_value = "SECRET_FINANCIAL_VALUE"
        assert captured.wait(4), private_value
        return [b"ok"]
    middleware = probe.SlowRequestProbe(blocked, logger, seconds=1)
    assert list(middleware({"PATH_INFO": "/reset/SECRET_TOKEN",
                            "HTTP_AUTHORIZATION": "SECRET_AUTH"}, Mock())) == [b"ok"]
    assert len(records) == 1
    assert any(row[2] == "blocked" for row in records[0]["stack_leaf_first"])
    assert "SECRET" not in json.dumps(records)
    assert middleware.slots._value == 16


def test_concurrent_requests_have_independent_timers(monkeypatch):
    timers = []
    class Timer:
        def __init__(self, seconds, callback):
            self.callback = callback
            self.cancelled = False
            timers.append(self)
        def start(self):
            pass
        def cancel(self):
            self.cancelled = True
    monkeypatch.setattr(probe.threading, "Timer", Timer)
    logger = Mock()
    middleware = probe.SlowRequestProbe(lambda e, s: [b"ok"], logger, seconds=1)
    a = middleware({}, Mock())
    b = middleware({}, Mock())
    a.close()
    timers[0].callback()  # Completion wins even if a timer callback was queued.
    logger.warning.assert_not_called()
    timers[1].callback()
    assert logger.warning.call_count == 1
    b.close()
    b.close()
    assert middleware.slots._value == 16


def test_stream_failure_and_close_cleanup():
    def stream():
        yield b"first"
        raise RuntimeError("stream")
    middleware = probe.SlowRequestProbe(lambda e, s: stream(), Mock(), seconds=1)
    response = middleware({}, Mock())
    with pytest.raises(RuntimeError):
        list(response)
    response.close()
    assert middleware.slots._value == 16


def test_timer_failure_and_capacity_fail_open(monkeypatch):
    middleware = probe.SlowRequestProbe(lambda e, s: [b"ok"], Mock(), seconds=1, max_pending=1)
    a = middleware({}, Mock())
    assert list(middleware({}, Mock())) == [b"ok"]
    a.close()
    monkeypatch.setattr(probe.threading.Timer, "start", Mock(side_effect=RuntimeError))
    assert list(middleware({}, Mock())) == [b"ok"]
    assert middleware.slots._value == 1


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan")])
def test_invalid_threshold(seconds):
    with pytest.raises(ValueError):
        probe.SlowRequestProbe(Mock(), Mock(), seconds=seconds)
