import importlib.util
from pathlib import Path
from unittest.mock import Mock, call
from concurrent.futures import ThreadPoolExecutor

import pytest

spec = importlib.util.spec_from_file_location(
    "db_connection_policy", Path(__file__).resolve().parents[1] / "utils/db_connection_policy.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def test_production_defaults_do_not_impose_statement_timeout():
    options = policy.production_connection_options({})
    assert options["pool_recycle"] == 120
    assert options["pool_timeout"] == 5
    assert options["connect_args"] == {
        "connect_timeout": 5, "keepalives": 1, "keepalives_idle": 15,
        "keepalives_interval": 5, "keepalives_count": 3, "tcp_user_timeout": 15000,
    }
    assert "options" not in options["connect_args"]


def test_explicit_overrides():
    options = policy.production_connection_options({
        "SQLALCHEMY_POOL_RECYCLE": "60", "SQLALCHEMY_POOL_TIMEOUT": "4",
        "DB_CONNECT_TIMEOUT_SECONDS": "3", "DB_TCP_USER_TIMEOUT_MS": "10000",
    })
    assert options["pool_recycle"] == 60
    assert options["pool_timeout"] == 4
    assert options["connect_args"]["connect_timeout"] == 3
    assert options["connect_args"]["tcp_user_timeout"] == 10000


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_reject_unbounded_values(value):
    with pytest.raises(ValueError):
        policy.production_connection_options({"DB_TCP_USER_TIMEOUT_MS": value})


def test_reset_before_dispatch_and_only_once(monkeypatch):
    pid = [100]
    monkeypatch.setattr(policy.os, "getpid", lambda: pid[0])
    calls = []
    engine = Mock()
    engine.dispose.side_effect = lambda **kw: calls.append(("dispose", kw))
    app = lambda e, s: calls.append(("app", {})) or [b"ok"]
    middleware = policy.ProcessLocalDatabasePools(app, [engine], Mock())
    middleware({}, Mock())
    assert calls == [("app", {})]
    pid[0] = 101
    middleware({}, Mock())
    middleware({}, Mock())
    assert calls[1:] == [("dispose", {"close": False}), ("app", {}), ("app", {})]
    engine.dispose.assert_called_once_with(close=False)


def test_concurrent_first_requests_reset_all_binds_once(monkeypatch):
    pid = [100]
    monkeypatch.setattr(policy.os, "getpid", lambda: pid[0])
    engines = [Mock(), Mock()]
    app = Mock(return_value=[b"ok"])
    middleware = policy.ProcessLocalDatabasePools(app, engines, Mock())
    pid[0] = 101
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: middleware({}, Mock()), range(16)))
    for engine in engines:
        engine.dispose.assert_called_once_with(close=False)
    assert app.call_count == 16


def test_application_error_is_never_replayed(monkeypatch):
    app = Mock(side_effect=RuntimeError("write failed"))
    middleware = policy.ProcessLocalDatabasePools(app, [], Mock())
    with pytest.raises(RuntimeError):
        middleware({}, Mock())
    app.assert_called_once()


def test_guard_is_inside_probe_and_before_dispatch():
    code = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert code.index("install_process_local_pools(app, db)") < code.index("install_slow_request_probe(app)")


def test_install_on_minimal_flask_runtime_without_database(monkeypatch):
    from flask import Flask
    from utils.slow_request_probe import install_slow_request_probe
    app = Flask('pool-integration')
    engine = Mock()
    db = Mock(engines={'default': engine})
    app.add_url_rule('/health', view_func=lambda: 'ok')
    policy.install_process_local_pools(app, db)
    guarded = app.wsgi_app
    install_slow_request_probe(app)
    assert app.wsgi_app is guarded  # diagnostic capture is disabled by default
    assert app.test_client().get('/health').data == b'ok'
    engine.dispose.assert_not_called()
    monkeypatch.setattr(policy.os, 'getpid', lambda: guarded.pid + 1)
    assert app.test_client().get('/health').status_code == 200
    engine.dispose.assert_called_once_with(close=False)
