from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
import pytest
from PIL import Image
from services.whatsapp_status_contracts import WeeklyStatusPlan, due_today, inspect_image, next_month
from services.whatsapp_status_provider import ZApiStatusProvider


def plan(**kwargs):
    return WeeklyStatusPlan(name='Versus semanal', weekly_arts={str(i): [i + 1] if i < 6 else [] for i in range(7)}, **kwargs).checked()


@pytest.mark.parametrize('when,expected', [('2026-10-05T11:29:59+00:00',False), ('2026-10-05T11:30:00+00:00',True),
    ('2026-10-05T11:34:59+00:00',True), ('2026-10-05T11:35:00+00:00',False), ('2026-10-04T11:30:00+00:00',False)])
def test_bahia_due_window_and_sunday(when,expected):
    assert due_today(plan(), datetime.fromisoformat(when), None) is expected


def test_no_repeat_and_naive_time_rejected():
    now = datetime.fromisoformat('2026-10-05T11:30:00+00:00')
    assert not due_today(plan(), now, now.date())
    with pytest.raises(ValueError): due_today(plan(), now.replace(tzinfo=None), None)


@pytest.mark.parametrize('payload', [ {'hour':True}, {'minute':60}, {'timezone':'UTC'}, {'url':'https://x'},
    {'weekly_arts':{'0':[1]}}, {'weekly_arts':{str(i):[True] for i in range(7)}},
    {'weekly_arts':{str(i):[1,1] for i in range(7)}}])
def test_strict_payload(payload):
    p = {'name':'Agenda','weekly_arts':{str(i):[] for i in range(7)}}; p.update(payload)
    with pytest.raises(ValueError): WeeklyStatusPlan.model_validate(p).checked()


def test_image_validation_and_monthly_review():
    b=BytesIO(); Image.new('RGB',(2,3),'red').save(b,format='PNG')
    assert inspect_image(b.getvalue())[1] == 'image/png'
    for data in (b'', b'<svg/>', b'https://example.com/a.png', b'x'*(8*1024*1024+1)):
        with pytest.raises(ValueError): inspect_image(data)
    assert next_month(datetime(2028,1,31,tzinfo=timezone.utc)).day == 29
    assert next_month(datetime(2026,12,31,tzinfo=timezone.utc)).year == 2027


@pytest.mark.parametrize('http,payload,state', [(200,{'messageId':'ABC123'},'accepted'), (200,{},'unknown'),
    (200,{'messageId':'https://secret/token'},'unknown'), (400,{},'failed'), (401,{},'failed'),
    (408,{},'unknown'), (429,{},'failed'), (500,{},'unknown'), (302,{},'unknown')])
def test_provider_states_and_no_raw_response(http,payload,state):
    calls=[]
    def post(url,**kw):
        calls.append(kw); return SimpleNamespace(status_code=http,json=lambda:payload)
    provider=ZApiStatusProvider({'instance_id':'INSTANCE','api_key':'SECRET','client_token':'CLIENT'},post=post)
    result=provider.send_image('data:image/png;base64,aaa')
    assert result.status == state
    assert 'SECRET' not in str(result) and 'CLIENT' not in str(result)
    assert len(calls)==1 and calls[0]['allow_redirects'] is False
    assert set(calls[0]['json']) == {'image'}


def test_timeout_never_retries_or_leaks(caplog):
    calls=[]
    def post(*a,**kw):
        calls.append(1); raise TimeoutError('https://api.z-api.io/token/SECRET')
    result=ZApiStatusProvider({'instance_id':'I','api_key':'SECRET','client_token':'C'},post=post).send_image('aaa')
    assert result.status == 'unknown' and len(calls)==1
    assert 'SECRET' not in str(result) + caplog.text


def test_device_masks_response_and_errors():
    cfg={'instance_id':'I','api_key':'SECRET','client_token':'C'}
    provider=ZApiStatusProvider(cfg,get=lambda url,**k:SimpleNamespace(status_code=200,
        json=lambda:{'connected':True} if url.endswith('/status') else {'phone':'55 (71) 99999-1234','about':'private'}))
    assert provider.connected_phone() == '5571999991234'
    provider._get=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('token/SECRET'))
    with pytest.raises(ValueError) as exc: provider.connected_phone()
    assert 'SECRET' not in str(exc.value)


@pytest.mark.parametrize('state',[False,None,'true',True])
def test_device_requires_strict_online_flag(state):
    calls=[]
    def get(url,**kw):
        calls.append(url.rsplit('/',1)[-1])
        return SimpleNamespace(status_code=200,json=lambda:{'connected':state} if url.endswith('/status') else {'phone':'5571999991234'})
    provider=ZApiStatusProvider({'instance_id':'I','api_key':'SECRET','client_token':'C'},get=get)
    if state is True:
        assert provider.connected_phone()=='5571999991234' and calls==['status','device']
    else:
        with pytest.raises(ValueError): provider.connected_phone()
        assert calls==['status']


def test_transport_debug_logging_redacts_token_paths(caplog):
    import logging
    with caplog.at_level(logging.DEBUG):
        logging.getLogger('urllib3.connectionpool').debug('POST %s', '/instances/I/token/VERYSECRET/send-image-status')
    assert 'VERYSECRET' not in caplog.text and '[REDACTED]' in caplog.text


@pytest.mark.parametrize('project_exists', [True, False])
def test_bundle_resolves_marketing_database_id_and_canonical_sequence(monkeypatch, project_exists):
    import sys
    from flask import Flask
    from services import whatsapp_status_service as svc
    calls = []
    monkeypatch.setattr(svc, 'authorize', lambda *args: None)
    monkeypatch.setitem(sys.modules, 'models.company', SimpleNamespace(Company=SimpleNamespace(
        query=SimpleNamespace(filter_by=lambda **kw: SimpleNamespace(first=lambda: SimpleNamespace(id=9))))))

    def project_query(**kw):
        calls.append(kw)
        return SimpleNamespace(first=lambda: SimpleNamespace(id=187) if project_exists else None)

    monkeypatch.setitem(sys.modules, 'models.project', SimpleNamespace(Project=SimpleNamespace(
        query=SimpleNamespace(filter_by=project_query))))
    with Flask('bundle_resolution_test').app_context():
        # Stop before any import/write; no configured source is intentional.
        expected = 'approved_source_not_staged' if project_exists else 'company_project_mismatch'
        with pytest.raises(ValueError, match=expected):
            svc.register_approved_bundle(9, 3, 1, 'versus_20261007')
    assert calls == [{'company_id': 9, 'id': 187, 'code_sequence': 26, 'is_deleted': False}]
