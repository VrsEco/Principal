from __future__ import annotations

import os

from app32.tests.e2e.config.contracts import validate_execution_contract
from app32.tests.e2e.config.environments import (
    E2EExecutionMode,
    load_environment_settings,
)


def test_dev_full_contract_defaults(monkeypatch):
    monkeypatch.delenv("E2E_DESTRUCTIVE_ACTIONS_ALLOWED", raising=False)
    monkeypatch.delenv("E2E_REQUIRES_ISOLATED_TENANT", raising=False)
    monkeypatch.delenv("E2E_REQUIRE_EXPLICIT_COMPANY", raising=False)
    monkeypatch.setenv("E2E_ENV_NAME", "DEV_FULL")
    monkeypatch.setenv("E2E_BASE_URL", "http://localhost:5002")
    monkeypatch.setenv("E2E_USERNAME", "dev@example.com")
    monkeypatch.setenv("E2E_PASSWORD", "secret")
    monkeypatch.setenv("E2E_COMPANY_ID", "9")

    settings = load_environment_settings()

    assert settings.execution_mode is E2EExecutionMode.DEV_FULL
    assert settings.destructive_actions_allowed is True
    validate_execution_contract(settings)


def test_prod_safe_contract_forbids_destructive(monkeypatch):
    monkeypatch.setenv("E2E_ENV_NAME", "PROD_SAFE")
    monkeypatch.setenv("E2E_BASE_URL", "https://app.gestaoversus.com.br")
    monkeypatch.setenv("E2E_USERNAME", "prod@example.com")
    monkeypatch.setenv("E2E_PASSWORD", "secret")
    monkeypatch.setenv("E2E_COMPANY_ID", "9")
    monkeypatch.setenv("E2E_DESTRUCTIVE_ACTIONS_ALLOWED", "false")

    settings = load_environment_settings()

    assert settings.execution_mode is E2EExecutionMode.PROD_SAFE
    assert settings.destructive_actions_allowed is False
    validate_execution_contract(settings)
