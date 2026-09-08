import pytest
from services.engineering_measurement_service import EngineeringMeasurement as Measurement, EngineeringMeasurementService as Service


@pytest.fixture
def pair():
    data=dict(workload_fingerprint='a'*64,identity_fingerprint='b'*64,evaluation_fingerprint='c'*64,
        runtime_fingerprint='d'*64,quality='pass',usage_source='provider_reported',input_tokens=100,output_tokens=100)
    return Measurement(**data,variant='baseline'),Measurement(**data,variant='candidate')


def test_real_and_estimated_are_separate(pair):
    before,after=pair
    before=before.model_copy(update={'estimated_context_tokens':1000})
    after=after.model_copy(update={'estimated_context_tokens':500})
    result=Service.compare(before,after)
    assert result['estimated_context']['reduction_percent']==50
    assert result['reported_total_tokens']['reduction_percent']==0
    assert result['cost_savings'] is None and not result['causal_savings_proven']


@pytest.mark.parametrize('key',['workload_fingerprint','identity_fingerprint','evaluation_fingerprint','runtime_fingerprint'])
def test_mismatch(pair,key):
    before,after=pair
    with pytest.raises(ValueError):Service.compare(before,after.model_copy(update={key:'f'*64}))


@pytest.mark.parametrize('quality',['fail','unknown'])
def test_quality_gate(pair,quality):
    before,after=pair
    result=Service.compare(before,after.model_copy(update={'quality':quality}))
    assert result['status']=='quality_not_established'
    assert result['reported_total_tokens']['reduction_percent'] is None


@pytest.mark.parametrize('change',[{'usage_source':'unknown'},{'input_tokens':None},{'output_tokens':None}])
def test_unknown_is_not_zero(pair,change):
    before,after=pair
    assert Service.compare(before,after.model_copy(update=change))['reported_total_tokens']['reduction_percent'] is None


def test_negative_savings_are_preserved(pair):
    before,after=pair
    result=Service.compare(before,after.model_copy(update={'input_tokens':300}))
    assert result['reported_total_tokens']['reduction_percent']==-100


def test_zero_baseline(pair):
    before,after=pair
    result=Service.compare(before.model_copy(update={'input_tokens':0,'output_tokens':0}),after)
    assert result['reported_total_tokens']['reduction_percent'] is None


def test_variants(pair):
    with pytest.raises(ValueError):Service.compare(pair[1],pair[0])


@pytest.mark.parametrize('value',[-1,True,1.5])
def test_strict_counts(pair,value):
    data=pair[0].model_dump();data['input_tokens']=value
    with pytest.raises(ValueError):Measurement(**data)


def test_no_identifiers_in_report(pair):
    result=str(Service.compare(*pair))
    assert 'a'*64 not in result and 'b'*64 not in result


@pytest.mark.parametrize('mode,code', [('pass',0),('mismatch',2),('malformed',2),('oversized',2),
    ('unknown',4),('quality',3),('zero',4),('overflow',2),('extra',2)])
def test_measurement_cli(pair,monkeypatch,capsys,mode,code):
    import importlib.util,io,json,sys
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('measurement_cli_test',Path(__file__).resolve().parents[1]/'scripts'/'compare_engineering_measurements.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    payload={'baseline':pair[0].model_dump(),'candidate':pair[1].model_dump()}
    if mode=='mismatch':payload['candidate']['identity_fingerprint']='f'*64
    if mode=='unknown':payload['candidate']['input_tokens']=None
    if mode=='quality':payload['candidate']['quality']='unknown'
    if mode=='zero':payload['baseline'].update(input_tokens=0,output_tokens=0)
    if mode=='overflow':payload['candidate']['input_tokens']=10**16
    if mode=='extra':payload['secret']='never print this'
    raw='private malformed' if mode=='malformed' else 'x'*65537 if mode=='oversized' else json.dumps(payload)
    monkeypatch.setattr(sys,'stdin',io.StringIO(raw))
    assert module.main()==code
    output=capsys.readouterr().out
    assert json.loads(output)['success']==(code!=2)
    assert 'never print this' not in output and 'private' not in output and 'a'*64 not in output
