"""Contrato das mutações do mcp-versus (onda 2): regras, e catraca sobre a linha de base."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.mcp_cohort_contract import ToolProbe, probe_registered_tools
from src.core.mcp_mutation_contract import (
    IDENTITY_PARAM,
    as_codes,
    audit_mutation_tool,
    is_mutation,
    survey_mutations,
)
from src.intelligence.tool_catalog import catalog

BASELINE = Path(__file__).parent / "data" / "mcp_mutation_violations_baseline.json"


def _cap(name="update_thing", *, risk="medium", gate=False, domain="routine", permissions=("x.edit",), scopes=("mcp_user",)):
    return SimpleNamespace(
        name=name,
        risk=SimpleNamespace(value=risk),
        human_gate=gate,
        domain=domain,
        permissions=permissions,
        scopes=scopes,
        tags=(),
        required_context=("company",),
    )


def _probe(*params, source="def t():\n    return 1\n"):
    return ToolProbe(schema={"properties": {p: {} for p in params}}, source=source, fn=None)


def _codes(name, cap, probe):
    return sorted({v.code for v in audit_mutation_tool(name, capability=cap, probe=probe)})


# ---- as regras --------------------------------------------------------------------------------
def test_a_clean_mutation_has_no_violation():
    assert _codes("update_thing", _cap(), _probe("company_id", "payload")) == []


def test_m1_company_must_be_top_level():
    assert _codes("update_thing", _cap(), _probe("payload")) == ["M1"]


@pytest.mark.parametrize("param", ["user_id", "approver_user_id", "actor_role", "request_id", "created_by_user_id"])
def test_m2_identity_from_the_client_is_rejected(param):
    assert "M2" in _codes("update_thing", _cap(), _probe("company_id", param))


def test_m2_does_not_reject_ordinary_ids():
    assert not IDENTITY_PARAM.match("employee_id") and not IDENTITY_PARAM.match("project_id")


def test_m3_write_verb_cannot_be_low_risk():
    assert "M3" in _codes("update_thing", _cap(risk="low"), _probe("company_id"))


@pytest.mark.parametrize("name", ["delete_thing", "remove_thing", "cancel_thing", "approve_thing", "publish_thing"])
def test_m4_is_satisfied_when_the_runtime_enforces_approval_for_the_class(name):
    """Decisão D6: o gate vale pelo que o runtime aplica (mcp_gate_policy), não pelo flag do catálogo."""
    assert "M4" not in _codes(name, _cap(name), _probe("company_id"))
    assert "M4" not in _codes(name, _cap(name, gate=True), _probe("company_id"))


def test_m4_flags_high_risk_that_the_runtime_would_not_gate(monkeypatch):
    monkeypatch.setattr("src.core.mcp_mutation_contract.requires_persisted_approval", lambda name, capability=None: False)
    assert "M4" in _codes("update_thing", _cap(risk="high"), _probe("company_id"))
    assert "M4" in _codes("delete_thing", _cap("delete_thing"), _probe("company_id"))


@pytest.mark.parametrize("param", ["confirm", "confirmed_mutation", "human_gate_confirmed"])
def test_m9_client_supplied_confirmation_is_rejected(param):
    assert "M9" in _codes("update_thing", _cap(), _probe("company_id", param))
    assert "M9" not in _codes("update_thing", _cap(), _probe("company_id", "payload"))


def test_m5_financial_creation_needs_idempotency():
    cap = _cap("create_financial_thing", domain="finance")
    assert "M5" in _codes("create_financial_thing", cap, _probe("company_id", "payload"))
    assert "M5" not in _codes("create_financial_thing", cap, _probe("company_id", "payload", "idempotency_key"))


def test_m6_missing_module_is_reported():
    source = "def t():\n    from services.modulo_que_nao_existe_xyz import X\n"
    assert "M6" in _codes("update_thing", _cap(), _probe("company_id", source=source))


def test_m7_unreachable_scope_or_missing_permission():
    assert "M7" in _codes("update_thing", _cap(scopes=("mcp_admin",)), _probe("company_id"))
    assert "M7" in _codes("update_thing", _cap(permissions=()), _probe("company_id"))


def test_m8_broad_except_must_let_permission_errors_through():
    swallow = "def t():\n    try:\n        x()\n    except Exception as exc:\n        return {'ok': False}\n"
    keep = "def t():\n    try:\n        x()\n    except PermissionError:\n        raise\n    except Exception as exc:\n        return {'ok': False}\n"
    assert "M8" in _codes("update_thing", _cap(), _probe("company_id", source=swallow))
    assert "M8" not in _codes("update_thing", _cap(), _probe("company_id", source=keep))


def test_is_mutation_covers_writes_and_skips_reads():
    assert is_mutation("create_meeting") and is_mutation("approve_agent_deployment")
    assert not is_mutation("list_meetings") and not is_mutation("get_meeting") and not is_mutation("answer_organizational_question_secure")


# ---- catraca sobre o catálogo real -------------------------------------------------------------
@pytest.fixture(scope="module")
def current():
    return as_codes(survey_mutations(probe_registered_tools(), list(catalog.iter_capabilities())))


@pytest.fixture(scope="module")
def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_no_new_violation_and_no_new_violating_tool(current, baseline):
    new = {
        name: sorted(set(codes) - set(baseline.get(name, ())))
        for name, codes in current.items()
        if set(codes) - set(baseline.get(name, ()))
    }
    assert not new, (
        "Violação NOVA no contrato de mutações (corrija a ferramenta; a linha de base só pode diminuir):\n"
        + "\n".join(f"  {name}: {', '.join(codes)}" for name, codes in sorted(new.items()))
    )


def test_baseline_only_shrinks(current, baseline):
    fixed = {
        name: sorted(set(codes) - set(current.get(name, ())))
        for name, codes in baseline.items()
        if set(codes) - set(current.get(name, ()))
    }
    assert not fixed, (
        "Violação corrigida: remova-a de tests/data/mcp_mutation_violations_baseline.json "
        "(python scripts/qa/mcp_mutation_report.py --write-baseline):\n"
        + "\n".join(f"  {name}: {', '.join(codes)}" for name, codes in sorted(fixed.items()))
    )


def test_every_published_mutation_is_known_to_the_report():
    report = survey_mutations(probe_registered_tools(), list(catalog.iter_capabilities()))
    assert len(report) >= 150, "o relatório deve cobrir as escritas do catálogo"


# ---- ferramentas JÁ PUBLICADAS corrigidas (D7) -------------------------------------------------
@pytest.mark.parametrize("name", ["delete_meeting_topic", "delete_meeting_decision", "delete_meeting_activity"])
def test_meeting_deletions_require_a_human_gate(name):
    capability = catalog.get_tool_capability(name)
    assert capability.human_gate is True and capability.human_gate_reason


@pytest.mark.parametrize(
    "name",
    ["create_whatsapp_status_schedule", "update_whatsapp_status_schedule", "pause_whatsapp_status_schedule"],
)
def test_whatsapp_schedule_writes_are_not_declared_low_risk(name):
    capability = catalog.get_tool_capability(name)
    assert getattr(capability.risk, "value", capability.risk) == "medium"
    # criar nasce desativada, editar pausa e pausar é parada de emergência: não levam gate; retomar leva.
    assert capability.human_gate is False


def test_resuming_a_whatsapp_schedule_keeps_its_gate_and_reads_stay_low():
    resume = catalog.get_tool_capability("resume_whatsapp_status_schedule")
    assert resume.human_gate is True and getattr(resume.risk, "value", resume.risk) == "high"
    for name in ("list_whatsapp_status_schedules", "verify_whatsapp_status_account"):
        assert getattr(catalog.get_tool_capability(name).risk, "value", None) == "low"
