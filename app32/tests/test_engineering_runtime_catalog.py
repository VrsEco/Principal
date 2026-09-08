import pytest
from services.engineering_runtime_catalog_service import read_codex_catalog


def rpc_for(pages, calls):
    pages=iter(pages)
    def rpc(method,params,notification=False):
        calls.append((method,params,notification))
        if method=='model/list':return next(pages)
        return {}
    return rpc


def test_read_only_paginated_projection():
    calls=[]
    pages=[{'data':[{'model':'example-a','supportedReasoningEfforts':[{'reasoningEffort':'low'}],'description':'private text'}],'nextCursor':'next'},
           {'data':[{'model':'hidden','hidden':True},{'model':'example-b'}],'nextCursor':None}]
    result=read_codex_catalog(rpc_for(pages,calls))
    assert [m['model'] for m in result['models']]==['example-a','example-b']
    assert not result['generation_access_verified'] and not result['automatic_switch']
    assert 'private text' not in str(result)
    assert [c[0] for c in calls]==['initialize','initialized','model/list','model/list']
    assert calls[-1][1]['cursor']=='next'


@pytest.mark.parametrize('page',[{}, {'data':'bad'}, {'data':[None]}, {'data':[{'model':''}]},
    {'data':[{'model':'a'},{'model':'a'}]}, {'data':[{'model':'a','supportedReasoningEfforts':[{}]}]},
    {'data':[],'nextCursor':False}])
def test_invalid_catalog_fails_closed(page):
    with pytest.raises(ValueError):read_codex_catalog(rpc_for([page],[]))


def test_pagination_bounded():
    with pytest.raises(ValueError):read_codex_catalog(rpc_for([{'data':[],'nextCursor':'again'}]*10,[]))


@pytest.mark.parametrize('mode',['success','missing','spawn','eof','malformed','rpc_error','timeout','cleanup','kill'])
def test_transport_with_fake_process(monkeypatch,capsys,mode):
    import importlib.util,io,json
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('catalog_transport_test',Path(__file__).resolve().parents[1]/'scripts'/'read_engineering_runtime_catalog.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sent=[]
    class Input(io.StringIO):
        def write(self,value):sent.append(json.loads(value));return super().write(value)
    class Process:
        stdin=Input()
        stdout=io.StringIO('\n'.join(json.dumps(x) for x in [
            {'id':1,'result':{}},{'id':3,'result':{'data':[{'model':'test-only'}],'nextCursor':None}}])+'\n')
        terminated=False
        killed=False
        def poll(self):return None
        def terminate(self):self.terminated=True
        def kill(self):self.killed=True
        def wait(self,timeout):
            if mode=='cleanup':raise OSError('private failure detail')
            if mode=='kill' and not self.killed:raise module.subprocess.TimeoutExpired('fake',timeout)
            return 0
    process=Process()
    if mode=='eof':process.stdout=io.StringIO('')
    if mode=='malformed':process.stdout=io.StringIO('private invalid json\n')
    if mode=='rpc_error':process.stdout=io.StringIO(json.dumps({'id':1,'error':{'message':'private detail'}})+'\n')
    class Worker:
        def __init__(self,target,**kwargs):self.target=target
        def start(self):self.target()
        def join(self,timeout):pass
        def is_alive(self):return False
    monkeypatch.setattr(module.threading,'Thread',Worker)
    monkeypatch.setattr(module.shutil,'which',lambda name:None if mode=='missing' else 'fake-codex.exe')
    def spawn(args,**kwargs):
        assert args==['fake-codex.exe','app-server','proxy']
        assert kwargs['stderr']==module.subprocess.DEVNULL
        if mode=='spawn':raise OSError('private path')
        return process
    monkeypatch.setattr(module.subprocess,'Popen',spawn)
    if mode=='timeout':
        ticks=iter([0,21])
        monkeypatch.setattr(module.time,'monotonic',lambda:next(ticks))
    expected=0 if mode in ('success','kill') else 2
    assert module.main()==expected
    result=json.loads(capsys.readouterr().out)
    assert result['success']==(expected==0)
    assert 'private' not in str(result)
    assert all(m['method'] in ('initialize','initialized','model/list') for m in sent)
    if mode not in ('missing','spawn'):assert process.terminated
    if mode=='kill':assert process.killed
