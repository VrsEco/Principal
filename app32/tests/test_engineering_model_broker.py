import pytest
from services.engineering_model_broker_service import EngineeringModelBrokerService as Broker, ModelPreference
from services.engineering_model_broker_service import RuntimeSelection
from services.engineering_task_router_service import EngineeringTaskRouterService as Router
from services.engineering_context_governor_service import EngineeringContextGovernorService as Governor
from services.instruction_registry_service import InstructionRegistryService as Registry
from src.intelligence.engineering_context import ContextIdentity


@pytest.fixture
def case():
    identity=ContextIdentity(repository_id='app32')
    task=Router.assess({'task_id':'m1','objective':'Corrigir cálculo','domain_hints':['backend_service']})
    bundle=Registry.resolve_bundle(runtime_profile='engineering')
    state=Governor.create(task,identity,bundle)
    packet=Governor.compose(state,identity,bundle,verified_sources={},budget_tokens=100000)
    return state,packet


def test_default_manual(case):
    result=Broker.recommend(*case)
    assert result.profile=='STANDARD' and result.model is None and result.provider is None
    assert not result.automatic_switch and not result.capabilities_verified


@pytest.mark.parametrize('mode,expected',[
    ('match','listed_for_manual_selection'),('no_effort','listed_for_manual_selection'),
    ('missing','manual_fallback'),('effort','manual_fallback'),('hidden','manual_fallback'),
    ('error','manual_fallback'),('blocked','blocked')])
def test_catalog_selection(case,mode,expected):
    calls=[]
    def rpc(method,params,notification=False):
        calls.append(method)
        if mode=='error':raise OSError('private runtime details')
        if method=='model/list':
            return {'data':[{'model':'example-only','hidden':mode=='hidden',
                'supportedReasoningEfforts':[{'reasoningEffort':'low'}]}],'nextCursor':None}
        return {}
    selection=RuntimeSelection(requested_model='missing' if mode=='missing' else 'example-only',
        requested_effort=None if mode=='no_effort' else 'high' if mode=='effort' else 'low')
    preference=ModelPreference(failure='security') if mode=='blocked' else None
    result=Broker.resolve_selection(*case,selection,rpc=rpc,preference=preference)
    assert result.status==expected and result.selection==selection
    assert not result.automatic_switch and not result.generation_access_verified
    assert result.recommendation.model is None
    assert 'private' not in result.model_dump_json()
    if mode=='blocked':assert calls==[]
    elif mode!='error':assert calls==['initialize','initialized','model/list']


def test_catalog_is_requeried_not_cached(case):
    pages=iter([{'data':[{'model':'example-only'}]}, {'data':[]}])
    def rpc(method,params,notification=False):
        return next(pages) if method=='model/list' else {}
    selection=RuntimeSelection(requested_model='example-only')
    assert Broker.resolve_selection(*case,selection,rpc=rpc).catalog_match
    assert not Broker.resolve_selection(*case,selection,rpc=rpc).catalog_match


def test_scope_mismatch_never_queries(case):
    state,packet=case
    def denied(*args,**kwargs):raise AssertionError('must not connect')
    with pytest.raises(ValueError):
        Broker.resolve_selection(state,packet.model_copy(update={'task_id':'other'}),
            RuntimeSelection(requested_model='example-only'),rpc=denied)


@pytest.mark.parametrize('values',[{'requested_model':''},{'requested_model':'x','requested_effort':''},
    {'requested_model':'x','catalog':{}},{'requested_model':123}])
def test_selection_contract(values):
    with pytest.raises(ValueError):RuntimeSelection(**values)


@pytest.mark.parametrize('change',[{'risk':'high'},{'complexity':'high'},{'requires_architect':True},{'requires_dba':True}])
def test_high_risk(case,change):
    state,packet=case
    state=state.model_copy(update={'assessment':state.assessment.model_copy(update=change)})
    result=Broker.recommend(state,packet,ModelPreference(profile='ECONOMY'))
    assert result.suggested_profile=='DEEP' and result.profile=='ECONOMY'
    assert result.preference_risk_warning and result.user_preference_preserved


def test_documentation_economy(case):
    state,packet=case
    state=state.model_copy(update={'assessment':state.assessment.model_copy(update={'task_type':'documentation','risk':'low','complexity':'low'})})
    assert Broker.recommend(state,packet).profile=='ECONOMY'


@pytest.mark.parametrize('failure',['security','uncertain_mutation','environment','requirement','test'])
def test_no_model_escalation_for_other_causes(case,failure):
    result=Broker.recommend(*case,ModelPreference(failure=failure,retries_used=5))
    assert result.suggested_profile is None and result.profile is None


@pytest.mark.parametrize('retries,expected',[(0,'STANDARD'),(1,'STANDARD'),(2,'DEEP')])
def test_implementation_review(case,retries,expected):
    assert Broker.recommend(*case,ModelPreference(failure='implementation',retries_used=retries)).profile==expected


def test_wrong_packet(case):
    state,packet=case
    with pytest.raises(ValueError):Broker.recommend(state,packet.model_copy(update={'task_id':'other'}))


@pytest.mark.parametrize('values',[{'profile':'cheap'},{'retries_used':True},{'retries_used':-1}])
def test_strict_input(values):
    with pytest.raises(ValueError):ModelPreference(**values)


def test_model_cli(case,monkeypatch,capsys):
    import importlib.util,io,json,sys
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('broker_cli_test',Path(__file__).resolve().parents[1]/'scripts'/'squad_engineering.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    request={'task':{'task_id':'m1','objective':'Corrigir cálculo','domain_hints':['backend_service']},
             'identity':case[0].identity.model_dump(),'broker_preference':{'profile':'DEEP'}}
    monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(request)))
    assert module.main(['model'])==0
    data=json.loads(capsys.readouterr().out)['data']
    assert data['profile']=='DEEP' and data['model'] is None and not data['automatic_switch']
