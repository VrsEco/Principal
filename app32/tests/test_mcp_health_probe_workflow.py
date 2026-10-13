"""O workflow agendado da sonda de saúde do mcp-versus: somente leitura, sem segredos e sem expor indisponibilidade."""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "mcp-health-probe.yml"
PROBE = ROOT / "app32" / "scripts" / "qa" / "mcp_health_probe.py"


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers(workflow):
    return workflow.get("on") or workflow.get(True)  # PyYAML lê "on" como booleano


def test_it_runs_on_a_schedule_and_can_be_dispatched(workflow):
    triggers = _triggers(workflow)
    assert triggers["schedule"][0]["cron"].split()[0] == "7,37", "a cada 30 min, fora do início da hora"
    assert "workflow_dispatch" in triggers


def test_it_is_read_only_and_uses_no_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text
    permissions = yaml.safe_load(text)["permissions"]
    assert permissions == {"contents": "read"}, "sem issues: o repositório é público e não deve revelar a indisponibilidade"


def test_it_runs_the_existing_probe_and_only_that_file_is_checked_out(workflow):
    steps = workflow["jobs"]["probe"]["steps"]
    assert PROBE.exists()
    joined = " ".join(str(step) for step in steps)
    assert "app32/scripts/qa/mcp_health_probe.py" in joined
    checkout = next(step for step in steps if str(step.get("uses", "")).startswith("actions/checkout"))
    assert "mcp_health_probe.py" in checkout["with"]["sparse-checkout"]


def test_a_failure_is_retried_once_and_only_a_failure_fails_the_job(workflow):
    steps = {step.get("name"): step for step in workflow["jobs"]["probe"]["steps"]}
    run = steps["Sonda (com uma nova tentativa em caso de falha)"]["run"]
    assert "sleep 60" in run and '-ge 2' in run, "retenta uma vez antes de reprovar"
    assert steps["Reprovar quando a sonda indica falha"]["if"] == "steps.probe.outputs.code == '2'"
    degraded = steps["Aviso de degradacao (nao reprova)"]
    assert degraded["if"] == "steps.probe.outputs.code == '1'" and "exit 1" not in degraded["run"]
    assert workflow["jobs"]["probe"]["timeout-minutes"] <= 5
