from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class E2ESuiteDefinition:
    suite_id: str
    label: str
    domain: str
    environments: tuple[str, ...]
    command_kind: str
    command_args: tuple[str, ...]
    destructive: bool
    summary: str

    def to_dict(self) -> dict:
        return {
            "suite_id": self.suite_id,
            "label": self.label,
            "domain": self.domain,
            "environments": list(self.environments),
            "command_kind": self.command_kind,
            "command_args": list(self.command_args),
            "destructive": self.destructive,
            "summary": self.summary,
        }


SUITE_CATALOG: dict[str, E2ESuiteDefinition] = {
    "smoke_real_navigation": E2ESuiteDefinition(
        suite_id="smoke_real_navigation",
        label="Smoke real de navegação",
        domain="smoke",
        environments=("DEV_FULL", "PROD_SAFE"),
        command_kind="pytest",
        command_args=("app32/tests/e2e/journeys/smoke/test_real_navigation_smoke.py", "-q"),
        destructive=False,
        summary="Login real e navegação crítica em my-work, meetings, api-mcp e channels.",
    ),
    "meetings_crud_devfull": E2ESuiteDefinition(
        suite_id="meetings_crud_devfull",
        label="CRUD meetings DEV_FULL",
        domain="meetings",
        environments=("DEV_FULL",),
        command_kind="pytest",
        command_args=("app32/tests/e2e/journeys/crud/test_meetings_crud_e2e.py", "-q"),
        destructive=True,
        summary="CRUD HTTP real de reuniões com massa controlada e cleanup.",
    ),
    "work_journey_manual_task_crud_devfull": E2ESuiteDefinition(
        suite_id="work_journey_manual_task_crud_devfull",
        label="CRUD work-journey DEV_FULL",
        domain="work_journey",
        environments=("DEV_FULL",),
        command_kind="pytest",
        command_args=("app32/tests/e2e/journeys/crud/test_work_journey_crud_e2e.py", "-q"),
        destructive=True,
        summary="CRUD HTTP real de tarefa avulsa da jornada de trabalho.",
    ),
    "user_concurrency_probe": E2ESuiteDefinition(
        suite_id="user_concurrency_probe",
        label="Probe multiusuário",
        domain="load",
        environments=("DEV_FULL",),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/run_user_concurrency_probe.py",),
        destructive=False,
        summary="Executa concorrência baseline com múltiplos usuários autenticados.",
    ),
    "mcp_concurrency_probe": E2ESuiteDefinition(
        suite_id="mcp_concurrency_probe",
        label="Probe MCP concorrente",
        domain="mcp",
        environments=("DEV_FULL",),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/run_mcp_concurrency_probe.py",),
        destructive=False,
        summary="Executa múltiplas sessões MCP autenticadas em paralelo.",
    ),
    "operational_reports": E2ESuiteDefinition(
        suite_id="operational_reports",
        label="Relatórios operacionais",
        domain="reporting",
        environments=("DEV_FULL", "PROD_SAFE"),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/build_operational_load_reports.py",),
        destructive=False,
        summary="Consolida relatórios operacionais de volume, multiusuário e MCP.",
    ),
    "report_filter_volume_probe": E2ESuiteDefinition(
        suite_id="report_filter_volume_probe",
        label="Probe de filtros e relatórios",
        domain="load",
        environments=("DEV_FULL", "PROD_SAFE"),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/run_report_filter_volume_probe.py",),
        destructive=False,
        summary="Executa stress funcional de filtros e relatórios críticos com perfis small/large/huge.",
    ),
    "report_download_probe": E2ESuiteDefinition(
        suite_id="report_download_probe",
        label="Probe de download de relatórios",
        domain="reporting",
        environments=("DEV_FULL", "PROD_SAFE"),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/run_report_download_probe.py",),
        destructive=False,
        summary="Valida emissão técnica do relatório printável do My Work.",
    ),
    "drift_detection": E2ESuiteDefinition(
        suite_id="drift_detection",
        label="Detector de drift funcional",
        domain="governance",
        environments=("DEV_FULL", "PROD_SAFE"),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/run_drift_detection.py",),
        destructive=False,
        summary="Compara inventário E2E com rotas críticas descobertas no app.",
    ),
    "execution_diff": E2ESuiteDefinition(
        suite_id="execution_diff",
        label="Diff entre execuções",
        domain="governance",
        environments=("DEV_FULL", "PROD_SAFE"),
        command_kind="python",
        command_args=("app32/tests/e2e/scripts/build_execution_diff.py",),
        destructive=False,
        summary="Compara os dois manifestos mais recentes e aponta regressões.",
    ),
}


def list_suite_catalog() -> list[E2ESuiteDefinition]:
    return list(SUITE_CATALOG.values())


def get_suite_definition(suite_id: str) -> E2ESuiteDefinition:
    try:
        return SUITE_CATALOG[suite_id]
    except KeyError as exc:
        raise KeyError(f"Suíte E2E não cadastrada: {suite_id}") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
