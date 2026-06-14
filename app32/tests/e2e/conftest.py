from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app32.tests.e2e.config.environments import E2EEnvironmentSettings, load_environment_settings
from app32.tests.e2e.core.browser_session import managed_page
from app32.tests.e2e.core.evidence import EvidenceCollector, EvidencePaths, create_evidence_paths
from app32.tests.e2e.core.reporter import ExecutionReporter
from app32.tests.e2e.data.run_context import RunContext


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: testes ponta a ponta com browser real")
    config.addinivalue_line("markers", "smoke: cobertura mínima operacional")
    config.addinivalue_line("markers", "dev_full: execução destrutiva autorizada apenas em DEV/HML")
    config.addinivalue_line("markers", "prod_safe: execução segura para produção controlada")


def pytest_collection_modifyitems(config, items):
    execution_mode = str(os.environ.get("E2E_ENV_NAME") or "DEV_FULL").strip().upper()
    if execution_mode == "PROD_SAFE":
        skip_dev_full = pytest.mark.skip(reason="DEV_FULL não roda em PROD_SAFE.")
        for item in items:
            if "dev_full" in item.keywords:
                item.add_marker(skip_dev_full)


@pytest.fixture(scope="session")
def e2e_settings() -> E2EEnvironmentSettings:
    return load_environment_settings()


@pytest.fixture(scope="session")
def e2e_evidence() -> EvidencePaths:
    settings = load_environment_settings()
    return create_evidence_paths(settings.outputs_dir)


@pytest.fixture(scope="session")
def e2e_collector(e2e_evidence: EvidencePaths) -> EvidenceCollector:
    return EvidenceCollector(e2e_evidence)


@pytest.fixture(scope="session")
def e2e_run_context(
    e2e_settings: E2EEnvironmentSettings,
    e2e_evidence: EvidencePaths,
    e2e_collector: EvidenceCollector,
) -> RunContext:
    return RunContext(
        settings=e2e_settings,
        evidence=e2e_evidence,
        collector=e2e_collector,
        reporter=ExecutionReporter(e2e_collector),
    )


@pytest.fixture
def page_context(
    e2e_settings: E2EEnvironmentSettings,
    e2e_evidence: EvidencePaths,
    e2e_collector: EvidenceCollector,
):
    with managed_page(e2e_settings, e2e_evidence, e2e_collector) as payload:
        yield payload
