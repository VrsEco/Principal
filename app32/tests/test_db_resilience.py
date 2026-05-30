from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.exc import OperationalError

from app32.utils import db_resilience


def _disconnect_error() -> OperationalError:
    return OperationalError(
        "SELECT 1",
        {},
        Exception("SSL error: decryption failed or bad record mac"),
    )


def test_is_transient_disconnect_error_detects_ssl_disconnect():
    assert db_resilience.is_transient_disconnect_error(_disconnect_error()) is True


def test_run_with_disconnect_retry_retries_once(monkeypatch):
    calls = {"count": 0}
    rollback_calls = {"count": 0}
    dispose_calls = {"count": 0}

    monkeypatch.setattr(db_resilience, "db", SimpleNamespace(
        session=SimpleNamespace(rollback=lambda: rollback_calls.__setitem__("count", rollback_calls["count"] + 1)),
        engine=SimpleNamespace(dispose=lambda: dispose_calls.__setitem__("count", dispose_calls["count"] + 1)),
    ))

    def _operation():
        calls["count"] += 1
        if calls["count"] == 1:
            raise _disconnect_error()
        return "ok"

    assert db_resilience.run_with_disconnect_retry(_operation) == "ok"
    assert calls["count"] == 2
    assert rollback_calls["count"] == 1
    assert dispose_calls["count"] == 1
