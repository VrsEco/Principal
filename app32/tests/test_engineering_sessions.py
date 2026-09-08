import json
import pytest
from services.engineering_task_router_service import EngineeringTaskRouterService as Router
from services.instruction_registry_service import InstructionRegistryService as Registry
from services.engineering_context_governor_service import EngineeringContextGovernorService as Governor
from services.engineering_session_service import EngineeringSessionService as Sessions
from services.engineering_handoff_service import EngineeringHandoffService as Handoffs
from src.intelligence.engineering_context import ContextIdentity,ContextItem


@pytest.fixture
def fixture():
    identity=ContextIdentity(repository_id='app32')
    task=Router.assess({'task_id':'t1','objective':'Corrigir cálculo'})
    bundle=Registry.resolve_bundle(runtime_profile='engineering')
    state=Governor.create(task,identity,bundle)
    ref=ContextItem(identity=identity,item_id='ref1',kind='file',source='services/example.py',version='v1',content='raw body never exported',reason='Necessário para teste')
    state=Governor.upsert(state,identity,ref)
    packet=Governor.compose(state,identity,bundle,verified_sources={'ref1':ref.fingerprint},budget_tokens=100000)
    return state,packet,ref


def checkpoint(fixture,**kwargs):
    state,packet,_=fixture
    return Handoffs.create(state,packet,summary='Regra revisada; implementação pendente.',reviewed_for_export=True,**kwargs)


def test_same_extend_rotate(fixture):
    state,packet,_=fixture
    assert Sessions.decide(state,state.assessment,state.identity,packet=packet).policy=='SAME'
    next_task=Router.assess({'task_id':'t2','objective':'Criar endpoint'})
    assert Sessions.decide(state,next_task,state.identity,depends_on=('t1',)).policy=='EXTEND'
    assert Sessions.decide(state,next_task,state.identity).policy=='ROTATE'


def test_identity_change_and_budget_force_rotation(fixture):
    state,packet,_=fixture
    identity=ContextIdentity(repository_id='other')
    result=Sessions.decide(state,state.assessment,identity)
    assert result.policy=='ROTATE' and not result.carries_context and not result.automatic_session_creation
    bundle=json.loads(state.registry_json)
    blocked=Governor.compose(state,state.identity,bundle,verified_sources={},budget_tokens=1)
    assert Sessions.decide(state,state.assessment,state.identity,packet=blocked).policy=='ROTATE'


@pytest.mark.parametrize('command',['status','context','why','model'])
def test_inspection_never_exposes_item_body(fixture,command):
    state,packet,_=fixture
    result=Sessions.inspect(command,state,packet)
    assert 'raw body' not in json.dumps(result)
    if command=='model':assert result['model'] is None and result['automatic_switch'] is False


def test_checkpoint_is_reference_only_and_requires_review(fixture):
    state,packet,_=fixture
    handoff=checkpoint(fixture)
    assert 'raw body' not in handoff.model_dump_json()
    with pytest.raises(ValueError):
        Handoffs.create(state,packet,summary='Teste',reviewed_for_export=False)


def test_save_load_and_no_overwrite(fixture,tmp_path):
    state,packet,ref=fixture
    path=Handoffs.save(tmp_path,'task-1.json',checkpoint(fixture))
    assert path.parent==tmp_path/'.ai'/'handoffs'
    with pytest.raises(FileExistsError):Handoffs.save(tmp_path,'task-1.json',checkpoint(fixture))
    loaded=Handoffs.load(tmp_path,'task-1.json',identity=state.identity,registry_fingerprint=packet.registry_fingerprint,verified_sources={'ref1':ref.fingerprint})
    assert loaded.execution_status=='not_resumed'


@pytest.mark.parametrize('name',['../outside.json','nested/a.json','C:\\tmp\\a.json','file.md','file.json:stream',''])
def test_bad_paths_rejected(fixture,tmp_path,name):
    with pytest.raises(ValueError):Handoffs.save(tmp_path,name,checkpoint(fixture))


@pytest.mark.parametrize('failure',['identity','registry','source','checksum','schema'])
def test_resume_fail_closed(fixture,tmp_path,failure):
    state,packet,ref=fixture
    path=Handoffs.save(tmp_path,'task.json',checkpoint(fixture))
    args={'identity':state.identity,'registry_fingerprint':packet.registry_fingerprint,'verified_sources':{'ref1':ref.fingerprint}}
    if failure=='identity':args['identity']=ContextIdentity(repository_id='other')
    if failure=='registry':args['registry_fingerprint']='0'*64
    if failure=='source':args['verified_sources']={}
    if failure in ('checksum','schema'):
        data=json.loads(path.read_text())
        data['handoff']['summary']='Modified' if failure=='checksum' else data['handoff']['summary']
        if failure=='schema':data['handoff']['schema_version']='future'
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):Handoffs.load(tmp_path,'task.json',**args)


@pytest.mark.parametrize('secret',['Bearer abc123456','password=not-for-export','sk-abcdefghijklmnopqrst'])
def test_common_secrets_rejected(fixture,secret):
    with pytest.raises(ValueError):checkpoint(fixture,decisions=(secret,))


def test_oversize_summary_rejected(fixture):
    state,packet,_=fixture
    with pytest.raises(ValueError):Handoffs.create(state,packet,summary='a'*1201,reviewed_for_export=True)


def test_stale_packet_rejected(fixture):
    state,packet,ref=fixture
    changed=Governor.transition(state,state.identity,ref.item_id,'WARM','Aguardar revisão')
    with pytest.raises(ValueError):Sessions.inspect('status',changed,packet)


def test_company_checkpoint_cannot_be_saved(fixture,tmp_path):
    identity=ContextIdentity(repository_id='repo',context_scope='company',company_id=1,user_id=1,permission_revision='verified-v1')
    handoff=checkpoint(fixture).model_copy(update={'identity':identity})
    with pytest.raises(ValueError):Handoffs.save(tmp_path,'task.json',handoff)
    assert not (tmp_path/'.ai').exists()


def test_symbolic_path_rejected(fixture,tmp_path,monkeypatch):
    from pathlib import Path
    original=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda path: path.name=='handoffs' or original(path))
    with pytest.raises(ValueError):Handoffs.save(tmp_path,'task.json',checkpoint(fixture))


def test_oversize_saved_file_rejected(fixture,tmp_path):
    state,packet,ref=fixture
    path=Handoffs.save(tmp_path,'task.json',checkpoint(fixture))
    path.write_bytes(b' '*40001)
    with pytest.raises(ValueError):Handoffs.load(tmp_path,'task.json',identity=state.identity,registry_fingerprint=packet.registry_fingerprint,verified_sources={'ref1':ref.fingerprint})


@pytest.mark.parametrize('command',['status','context','why','model','decide','handoff','resume'])
def test_cli_commands(fixture,tmp_path,monkeypatch,capsys,command):
    import importlib.util,io,sys
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'scripts'/'squad_engineering.py'
    spec=importlib.util.spec_from_file_location('session_cli_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'APP_ROOT',tmp_path)
    state,packet,ref=fixture
    request={'task':{'task_id':'t1','objective':'Corrigir cálculo'},'identity':state.identity.model_dump(),'items':[ref.model_dump()],
             'next_task':{'task_id':'t2','objective':'Criar endpoint'},'name':'task.json','summary':'Revisão pendente','reviewed_for_export':True}
    if command=='resume':Handoffs.save(tmp_path,'task.json',checkpoint(fixture))
    monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(request)))
    assert module.main([command])==0
    assert json.loads(capsys.readouterr().out)['success']
