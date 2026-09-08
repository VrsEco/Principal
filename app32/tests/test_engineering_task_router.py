import json

import pytest
from pydantic import ValidationError

from services.engineering_task_router_service import EngineeringTaskRouterService as Router
from src.intelligence.engineering_assessment import EngineeringTaskRequest
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


def assess(objective, **kwargs):
    return Router.assess({'task_id': 'unit-1', 'objective': objective, **kwargs})


@pytest.mark.parametrize('objective,domain', [
    ('Trocar a cor do botão', 'frontend'),
    ('Corrigir cálculo acumulado', 'backend_service'),
    ('Criar endpoint REST', 'backend_api'),
    ('Revisar query PostgreSQL', 'dba'),
    ('Investigar RAG', 'ai_engineer'),
    ('Executar regressão pytest', 'qa_automation'),
    ('Revisar arquitetura', 'arquiteto'),
])
def test_routes_known_domains(objective, domain):
    result = assess(objective)
    assert result.entry_agent == 'SE-COORD'
    assert result.domain == domain
    assert result.specialists[0] == f'harness_{domain}_engenharia_v1'
    assert not result.requires_clarification


@pytest.mark.parametrize('objective', ['Alterar login', 'Corrigir company_id', 'Trocar permissão de botão'])
def test_security_overrides_size_and_frontend(objective):
    result = assess(objective, files=['static/button.css'])
    assert result.domain == 'arquiteto'
    assert result.requires_architect and result.risk == 'high'


def test_migration_with_auth_requires_both_architect_and_dba():
    result = assess('Migração de autenticação', task_type='maintenance')
    assert result.specialists == ('harness_arquiteto_engenharia_v1', 'harness_dba_engenharia_v1', 'harness_qa_automation_engenharia_v1')
    assert result.requires_architect and result.requires_dba


def test_migration_beats_service_hint():
    result = assess('Criar migration', domain_hints=['backend_service'])
    assert result.domain == 'dba' and result.risk == 'high'


@pytest.mark.parametrize('objective', ['Melhore isso', 'Criar layout e endpoint'])
def test_unknown_or_ambiguous_keeps_coordination(objective):
    result = assess(objective)
    assert result.domain == 'unknown'
    assert result.requires_clarification and result.unknowns
    assert result.specialists == ()


def test_file_signals_and_stable_input_order():
    one = assess('Ajuste pontual', files=['tests/test_a.py', 'services/a.py'], domain_hints=['backend_service'])
    two = assess('Ajuste pontual', files=['services/a.py', 'tests/test_a.py', 'services/a.py'], domain_hints=['backend_service'])
    assert one == two
    assert one.domain == 'backend_service'


@pytest.mark.parametrize('payload', [
    {'context_scope': 'company'},
    {'company_id': 9},
    {'context_scope': 'company', 'company_id': True},
    {'context_scope': 'company', 'company_id': 0},
    {'context_scope': 'company', 'company_id': '9'},
    {'domain_hints': ['finance']},
    {'runtime_profile': 'squad_cliente'},
    {'surface': 'admin'},
    {'files': ['../secret']},
    {'objective': ' '},
])
def test_strict_payload_and_no_authority_fields(payload):
    with pytest.raises(ValidationError):
        Router.assess({'task_id': 'unit-1', 'objective': 'Verificar cálculo', **payload})


def test_company_scope_does_not_leak_between_requests():
    one = assess('Verificar cálculo', context_scope='company', company_id=9)
    two = assess('Verificar cálculo', context_scope='company', company_id=10)
    assert one.company_id == 9 and two.company_id == 10
    assert one.telemetry()['company_id'] == 9
    assert assess('Verificar cálculo').company_id is None


def test_telemetry_redacts_objective_paths_and_task_identifier():
    result = Router.assess(EngineeringTaskRequest(task_id='sensitive-id', objective='Corrigir cálculo secret-123', files=('services/private.py',)))
    text = json.dumps(result.telemetry())
    assert all(value not in text for value in ('secret-123', 'private.py', 'sensitive-id'))
    assert result.telemetry()['tokens'] is None
    assert result.telemetry()['status'] == 'assessed_not_executed'


def test_router_fails_closed_when_harness_missing(monkeypatch):
    from dataclasses import replace
    import services.engineering_task_router_service as module
    spec = get_runtime_profile_spec('engineering')
    monkeypatch.setattr(module, 'get_runtime_profile_spec', lambda _: replace(spec, harnesses=()))
    with pytest.raises(ValueError, match='não registrado'):
        assess('Trocar CSS')


def test_qa_is_recommended_only_when_needed():
    assert len(assess('Revisar cálculo').specialists) == 1
    assert assess('Corrigir cálculo', task_type='maintenance').specialists[-1] == 'harness_qa_automation_engenharia_v1'


@pytest.mark.parametrize('objective,kind', [
    ('Corrigir cálculo', 'maintenance'), ('Criar endpoint', 'feature'),
    ('Documentar arquitetura', 'documentation'), ('Incidente no endpoint', 'incident'),
    ('Analisar cálculo', 'diagnosis'),
])
def test_task_type_inferred_when_not_supplied(objective, kind):
    assert assess(objective).task_type == kind


def test_explicit_task_type_cannot_hide_incident_risk():
    result = assess('Incidente no endpoint', task_type='documentation')
    assert result.risk == 'high'


def test_bootstrap_publishes_local_advisory_contract():
    from src.core.mcp_squad_runtime_tools import register_squad_runtime_tools
    class FakeMCP:
        def tool(self):
            def register(fn):
                self.fn = fn
                return fn
            return register
    mcp = FakeMCP()
    register_squad_runtime_tools(mcp)
    result = mcp.fn(runtime_profile='engineering')['data']
    assert result['entry_agent']['key'] == 'SE-COORD'
    assert result['task_assessment']['execution_mode'] == 'local_advisory'
    assert result['task_assessment']['grants_permissions'] is False
    assert result['task_assessment']['executes_specialists'] is False
    assert result['task_assessment']['model_selection'] == 'manual_outside_assessment'
    assert result['task_assessment']['reads_operational_data'] is False
    assert len({h['agent_key'] for h in result['harnesses']}) == 8


@pytest.mark.parametrize('harness', get_runtime_profile_spec('engineering').harnesses)
def test_registry_uses_canonical_specialist_identity(harness):
    from services.instruction_registry_service import InstructionRegistryService
    bundle = InstructionRegistryService.resolve_bundle(runtime_profile='engineering', harness_key=harness.key)
    assert bundle['agent_key'] == harness.agent_key
    assert bundle['harness_key'] == harness.key
    assert bundle['surface'] == 'ops'


@pytest.mark.parametrize('kwargs', [
    {'harness_key': 'harness_operacional_cliente_v1'},
    {'harness_key': 'harness_frontend_engenharia_v1', 'agent_key': 'SE-COORD'},
])
def test_registry_rejects_cross_family_or_identity_mismatch(kwargs, monkeypatch):
    from services.instruction_registry_service import InstructionRegistryService
    def forbid_sync():
        raise AssertionError('Invalid identity must fail before database bootstrap')
    monkeypatch.setattr(InstructionRegistryService, 'sync_defaults', forbid_sync)
    with pytest.raises(ValueError):
        InstructionRegistryService.resolve_bundle(runtime_profile='engineering', **kwargs)


def test_canonical_registry_preserves_all_eight_harnesses():
    spec = get_runtime_profile_spec('engineering')
    assert len(spec.harnesses) == 8
    assert len({h.agent_key for h in spec.harnesses}) == 8
    assert spec.default_harness_key == 'harness_coordenador_engenharia_v1'
    assert spec.allowed_surfaces == ('ops', 'admin', 'analytics')


@pytest.mark.parametrize('raw,code,success', [
    ('{"task_id":"cli-1","objective":"Corrigir calculo"}', 0, True),
    ('{"task_id":"cli-1","objective":"Corrigir calculo","surface":"admin"}', 2, False),
    ('invalid-secret', 2, False),
])
def test_local_entrypoint(monkeypatch, capsys, raw, code, success):
    import importlib.util
    import io
    from pathlib import Path
    import sys
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'assess_engineering_task.py'
    spec = importlib.util.spec_from_file_location('engineering_cli_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, 'stdin', io.StringIO(raw))
    assert module.main() == code
    output = capsys.readouterr().out
    assert json.loads(output)['success'] is success
    if not success:
        assert 'invalid-secret' not in output
