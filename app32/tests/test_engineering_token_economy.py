import json

import pytest

from services.engineering_task_router_service import EngineeringTaskRouterService as Router
from services.engineering_token_economy_service import EngineeringTokenEconomyService as Adviser


def assess(objective, **kwargs):
    return Router.assess({'task_id': 'economy-1', 'objective': objective, **kwargs})


@pytest.mark.parametrize('intent,complexity,strategy', [
    ('execution', 'low', 'minimal_active'),
    ('correction', 'medium', 'symbol_and_delta'),
    ('planning', 'high', 'architecture_then_expand'),
])
def test_explicit_intent_controls_complexity_and_context_strategy(intent, complexity, strategy):
    assessment = assess('Ação delimitada', task_intent=intent, domain_hints=['backend_service'])
    advice = Adviser.advise(assessment)
    assert assessment.task_intent == intent
    assert assessment.complexity == complexity
    assert advice.strategy == strategy
    assert advice.selects_model is False
    assert advice.estimated_token_savings is None


def test_correction_is_inferred_as_medium():
    assessment = assess('Corrigir cálculo acumulado')
    assert assessment.task_intent == 'correction'
    assert assessment.complexity == 'medium'
    assert Adviser.advise(assessment).strategy == 'symbol_and_delta'


def test_planning_is_inferred_as_high_without_claiming_high_risk():
    assessment = assess('Planejamento da integração de relatórios')
    assert assessment.task_intent == 'planning'
    assert assessment.complexity == 'high'
    assert assessment.risk != 'high'


def test_security_cannot_be_downgraded_by_execution_intent():
    assessment = assess('Ajustar company_id', task_intent='execution')
    advice = Adviser.advise(assessment)
    assert assessment.complexity == 'high'
    assert assessment.risk == 'high'
    assert advice.requires_authenticated_mcp


def test_ambiguous_request_clarifies_before_context_expansion():
    assessment = assess('Criar layout e endpoint')
    advice = Adviser.advise(assessment)
    assert assessment.requires_clarification
    assert advice.strategy == 'clarify_before_expand'
    assert 'Confirmar domínio líder' in advice.next_action


def test_company_context_requires_authenticated_mcp_but_grants_nothing():
    assessment = assess('Executar ajuste', task_intent='execution', context_scope='company', company_id=7,
                        domain_hints=['backend_service'])
    advice = Adviser.advise(assessment)
    assert advice.requires_authenticated_mcp
    assert advice.advisory_only
    assert assessment.company_id == 7


def test_advice_telemetry_has_no_task_content_or_model_choice():
    assessment = assess('Corrigir secret-123', files=['services/private.py'])
    data = Adviser.advise(assessment).telemetry()
    encoded = json.dumps(data)
    assert 'secret-123' not in encoded
    assert 'private.py' not in encoded
    assert data['selects_model'] is False
    assert data['estimated_token_savings'] is None


@pytest.mark.parametrize('payload', [
    {'task_intent': 'model_selection'},
    {'task_intent': True},
    {'task_intent': 'execution', 'model': 'gpt-anything'},
])
def test_intent_contract_rejects_model_selection_or_unknown_values(payload):
    with pytest.raises(Exception):
        Router.assess({'task_id': 'economy-1', 'objective': 'Ação delimitada', **payload})


def test_cli_returns_assessment_and_context_advice_not_model_recommendation(monkeypatch, capsys):
    import importlib.util
    import io
    from pathlib import Path
    import sys
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'assess_engineering_task.py'
    spec = importlib.util.spec_from_file_location('economy_cli_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = json.dumps({'task_id': 'cli-economy', 'objective': 'Corrigir cálculo', 'task_intent': 'correction'})
    monkeypatch.setattr(sys, 'stdin', io.StringIO(raw))
    assert module.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data['assessment']['complexity'] == 'medium'
    assert data['token_economy']['strategy'] == 'symbol_and_delta'
    assert data['token_economy']['selects_model'] is False
    assert 'model' not in data['token_economy']
