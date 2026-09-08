import pytest
from services.engineering_quality_gate_service import EngineeringQualityGateService as Gate, QualityEvidence, QualityPolicy
from services.engineering_task_router_service import EngineeringTaskRouterService as Router
from services.engineering_context_governor_service import EngineeringContextGovernorService as Governor
from services.instruction_registry_service import InstructionRegistryService as Registry
from src.intelligence.engineering_context import ContextIdentity


@pytest.fixture
def case():
    identity=ContextIdentity(repository_id='app32')
    task=Router.assess({'task_id':'qa1','objective':'Corrigir cálculo','domain_hints':['backend_service']})
    bundle=Registry.resolve_bundle(runtime_profile='engineering')
    state=Governor.create(task,identity,bundle)
    packet=Governor.compose(state,identity,bundle,verified_sources={},budget_tokens=100000)
    evidence=QualityEvidence(task_id=task.task_id,identity_fingerprint=identity.fingerprint,
        packet_fingerprint=packet.fingerprint,requirements='pass',limited_diff='pass',tests='pass',
        regression='pass',documentation='pass',evidence_refs=('local-test-report',))
    return state,packet,evidence


def test_local_only(case):
    result=Gate.evaluate(*case)
    assert result.status=='local_validated'
    assert not result.automatic_execution and not result.evidence_verified


@pytest.mark.parametrize('check',['requirements','limited_diff','tests','regression','documentation'])
@pytest.mark.parametrize('value',['unknown','fail'])
def test_missing_or_failed_check_blocks(case,check,value):
    state,packet,evidence=case
    assert Gate.evaluate(state,packet,evidence.model_copy(update={check:value})).status=='blocked'


@pytest.mark.parametrize('value',['unknown','pass','fail'])
def test_no_operational_pass_from_declaration(case,value):
    state,packet,evidence=case
    result=Gate.evaluate(state,packet,evidence.model_copy(update={'operational':value}),target='operational')
    assert result.status==('blocked' if value=='fail' else 'remote_validation_pending')


@pytest.mark.parametrize('failure,action',[
    ('security','stop_and_request_human_review'),('uncertain_mutation','stop_and_request_human_review'),
    ('requirement','clarify_with_coordinator'),('environment','repair_environment'),
    ('test','diagnose_test_vs_regression'),('implementation','diagnose_before_manual_retry')])
def test_failure_classification(case,failure,action):
    state,packet,evidence=case
    result=Gate.evaluate(state,packet,evidence.model_copy(update={'failure':failure}))
    assert result.status=='blocked' and result.action==action and not result.provider_escalation


@pytest.mark.parametrize('retries,escalations,action',[(1,0,'diagnose_before_manual_retry'),
    (2,0,'request_specialist_review'),(2,1,'stop_and_request_human_review'),(99,99,'stop_and_request_human_review')])
def test_retry_boundaries(case,retries,escalations,action):
    state,packet,evidence=case
    result=Gate.evaluate(state,packet,evidence.model_copy(update={'failure':'implementation','retries_used':retries,'escalations_used':escalations}))
    assert result.action==action


@pytest.mark.parametrize('field',['task_id','identity_fingerprint','packet_fingerprint'])
def test_scope_and_revision_binding(case,field):
    state,packet,evidence=case
    with pytest.raises(ValueError):Gate.evaluate(state,packet,evidence.model_copy(update={field:'0'*64}))


@pytest.mark.parametrize('refs',[(),(' ',),('a'*401,)])
def test_evidence_reference_required(case,refs):
    state,packet,evidence=case
    assert Gate.evaluate(state,packet,evidence.model_copy(update={'evidence_refs':refs})).status=='blocked'


@pytest.mark.parametrize('values',[{'max_retries':True},{'max_retries':-1},{'max_retries':6},{'max_escalations':4}])
def test_limits_strict(values):
    with pytest.raises(ValueError):QualityPolicy(**values)


@pytest.mark.parametrize('flag,check',[('requires_architect','architecture'),('requires_dba','database_review')])
def test_specialist_reviews_required(case,flag,check):
    state,packet,evidence=case
    state=state.model_copy(update={'assessment':state.assessment.model_copy(update={flag:True})})
    result=Gate.evaluate(state,packet,evidence.model_copy(update={'tenant_policy':'pass'}))
    assert result.status=='blocked' and check in result.reasons


def test_zero_limits_stop(case):
    state,packet,evidence=case
    result=Gate.evaluate(state,packet,evidence.model_copy(update={'failure':'implementation'}),policy=QualityPolicy(max_retries=0,max_escalations=0))
    assert result.action=='stop_and_request_human_review'


@pytest.mark.parametrize('mode',['missing','pass','remote','failed','mismatch','status','why','context','handoff','invalid'])
def test_quality_cli(case,monkeypatch,capsys,mode):
    import importlib.util
    import io
    import json
    import sys
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'scripts'/'squad_engineering.py'
    spec=importlib.util.spec_from_file_location('quality_cli_test',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state,packet,evidence=case
    request={'task':{'task_id':'qa1','objective':'Corrigir cálculo','domain_hints':['backend_service']},
             'identity':state.identity.model_dump(),'budget_tokens':100000}
    command=mode if mode in ('status','why','context','handoff') else 'qa'
    if mode not in ('missing','context'):
        request['quality_evidence']=evidence.model_dump()
    expected=0
    if mode=='missing':expected=3
    if mode=='remote':request['quality_target']='operational';expected=4
    if mode=='failed':request['quality_evidence']['tests']='fail';expected=3
    if mode=='mismatch':request['quality_evidence']['packet_fingerprint']='0'*64;expected=2
    if mode=='invalid':request['quality_policy']={'max_retries':True};expected=2
    if mode=='handoff':expected=2
    monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(request)))
    assert module.main([command])==expected
    output=json.loads(capsys.readouterr().out)
    assert output['success']==(expected!=2)
    assert 'local-test-report' not in json.dumps(output)
    if mode=='context':assert output['data']['evidence_binding']['packet_fingerprint']==packet.fingerprint
    if mode in ('pass','status','why'):assert output['data']['quality_gate']['status']=='local_validated'
    if mode=='remote':assert output['data']['quality_gate']['status']=='remote_validation_pending'
