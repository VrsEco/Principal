"""O runtime MCP reaproveita um único app Flask (e um pool de banco) por processo."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from flask import Flask

import src.core.mcp_flask_app as shared


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setattr(shared, "_apps", {})


def _factory(monkeypatch):
    built = []

    def create_app(config_name=None):
        built.append(config_name)
        return Flask(f"probe-{len(built)}")

    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(create_app=create_app))
    return built


def test_many_calls_build_the_app_once(monkeypatch):
    built = _factory(monkeypatch)
    apps = {id(shared.get_mcp_flask_app()) for _ in range(25)}
    assert len(apps) == 1 and built == [None]


def test_each_configuration_is_built_once(monkeypatch):
    built = _factory(monkeypatch)
    shared.get_mcp_flask_app("production")
    shared.get_mcp_flask_app("production")
    shared.get_mcp_flask_app()
    assert sorted(map(str, built)) == ["None", "production"]


def test_existing_context_is_reused_without_building(monkeypatch):
    built = _factory(monkeypatch)
    outer = Flask("outer")
    with outer.app_context():
        assert shared.get_mcp_flask_app() is outer
    assert built == []


def test_a_replaced_factory_is_not_served_a_stale_app(monkeypatch):
    _factory(monkeypatch)
    first = shared.get_mcp_flask_app()
    _factory(monkeypatch)
    assert shared.get_mcp_flask_app() is not first
