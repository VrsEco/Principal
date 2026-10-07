"""Real PostgreSQL migration/locks/ledger tests; never uses app .env or production."""
import importlib.util
from datetime import datetime, timezone, timedelta
from io import BytesIO
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from sqlalchemy import text
from sqlalchemy.engine import make_url
from services import whatsapp_status_service as svc
from services.whatsapp_status_provider import StatusResult


@pytest.fixture
def lab(monkeypatch,tmp_path):
    url=os.getenv('APP32_STATUS_TEST_DATABASE_URL')
    if not url: pytest.skip('Requires explicitly configured disposable PostgreSQL')
    parsed=make_url(url)
    assert parsed.host=='127.0.0.1' and parsed.port==55439 and parsed.database=='whatsapp_status_test'
    app=Flask('status_test'); app.config.update(SQLALCHEMY_DATABASE_URI=url, WHATSAPP_STATUS_PRIVATE_ROOT=str(tmp_path), WHATSAPP_STATUS_ENABLED=True)
    db=SQLAlchemy(app)
    for name in ('companies','users','projects','identity_principals'):
        db.Table(name,db.Column('id',db.Integer,primary_key=True))
    pkg=ModuleType('_status_test_models'); pkg.db=db; pkg.__path__=[]
    monkeypatch.setitem(sys.modules,'_status_test_models',pkg)
    path=Path(__file__).resolve().parents[1]/'models/whatsapp_status.py'
    spec=importlib.util.spec_from_file_location('_status_test_models.whatsapp_status',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    types=(db,mod.WhatsAppStatusAccount,mod.WhatsAppStatusArt,mod.WhatsAppStatusBatch,mod.WhatsAppStatusPublication,mod.WhatsAppStatusSchedule)
    monkeypatch.setattr(svc,'_models',lambda:types)
    monkeypatch.setattr(svc,'authorize',lambda *args:None)
    provider=SimpleNamespace(calls=[],phone='5571999991234',result=StatusResult('accepted','provider_accepted','A123'))
    provider.connected_phone=lambda:provider.phone
    def send(data): provider.calls.append(data); return provider.result
    provider.send_image=send
    monkeypatch.setattr(svc,'_provider',lambda account:provider)
    with app.app_context():
        db.metadata.drop_all(db.engine)
        db.metadata.create_all(db.engine,tables=[db.metadata.tables[n] for n in ('companies','users','projects','identity_principals')])
        mspec=importlib.util.spec_from_file_location('status_migration',path.parents[1]/'migrations/versions/20261007_1000_whatsapp_status.py')
        migration=importlib.util.module_from_spec(mspec); mspec.loader.exec_module(migration)
        with db.engine.begin() as conn:
            conn.execute(text(migration.DDL))
            for n in ('companies','users','projects','identity_principals'):
                conn.execute(text(f'INSERT INTO {n}(id) VALUES (1),(2)'))
        Account,Art,Batch,Pub,Schedule=types[1:]
        db.session.add(Account(company_id=1,integration_id='existing',expected_phone=provider.phone,
                               verified_at=datetime.now(timezone.utc),status_tested_at=datetime.now(timezone.utc),enabled=True))
        for i in range(1,4):
            b=BytesIO(); Image.new('RGB',(3,3),(i*30,0,0)).save(b,format='PNG'); data=b.getvalue()
            from services.whatsapp_status_contracts import inspect_image
            sha,mime=inspect_image(data); root=tmp_path/'1'; root.mkdir(exist_ok=True); (root/f'{i}.bin').write_bytes(data)
            db.session.add(Art(id=i,company_id=1,project_id=1,kit_code='versus',kit_size=3,code=f'versus-0{i}',version=1,
                               position=i,private_path=f'{i}.bin',sha256=sha,mime=mime,approved_by=1))
        db.session.commit()
        yield SimpleNamespace(db=db,app=app,Account=Account,Art=Art,Batch=Batch,Pub=Pub,Schedule=Schedule,provider=provider,root=tmp_path)
        db.session.remove(); db.metadata.drop_all(db.engine); db.engine.dispose()


def weekly(lab):
    return svc.save_schedule(1,1,1,{'name':'Versus semanal','weekly_arts':{str(i):[1,2,3] if i<6 else [] for i in range(7)}})


def test_kit_order_acceptance_dedupe_and_mobile(lab):
    first=svc.publish_kit(1,1,1,'versus',1,'command:one')
    assert first['status']=='accepted' and [r['art_id'] for r in first['results']]==[1,2,3]
    assert not any(r['mobile_confirmed'] for r in first['results'])
    assert len(lab.provider.calls)==3
    assert svc.publish_kit(1,1,1,'versus',1,'command:one')==first
    assert len(lab.provider.calls)==3
    with pytest.raises(ValueError,match='duplicate'): svc.publish(1,1,1,[1],'command:two')
    with pytest.raises(ValueError,match='payload_conflict'): svc.publish(1,1,1,[1],'command:one')
    svc.confirm_mobile(1,1,1,first['results'][0]['id'])
    assert svc.list_results(1,1,1)['batches'][0]['results'][0]['mobile_confirmed']


@pytest.mark.parametrize('state',['unknown','failed'])
def test_failure_stops_kit_no_automatic_retry(lab,state):
    lab.provider.result=StatusResult(state,'safe_code')
    first=svc.publish_kit(1,1,1,'versus',1,'command:one')
    assert first['status']==state and len(lab.provider.calls)==1
    svc.publish_kit(1,1,1,'versus',1,'command:one')
    assert len(lab.provider.calls)==1


def test_crash_after_acceptance_before_commit_is_unknown_not_resent(lab):
    def crash(data): lab.provider.calls.append(data); raise SystemExit('simulate crash')
    lab.provider.send_image=crash
    with pytest.raises(SystemExit): svc.publish(1,1,1,[1],'command:one')
    lab.db.session.remove()  # actual new DB session simulates process restart
    assert lab.Pub.query.one().status=='sending'
    result=svc.publish(1,1,1,[1],'command:one')
    assert result['status']=='unknown' and result['results'][0]['status']=='unknown'
    assert len(lab.provider.calls)==1


def test_concurrent_connection_cannot_enter_company_lock(lab):
    with svc.company_lock(1):
        with pytest.raises(ValueError,match='busy'):
            with svc.company_lock(1): pass
        with svc.company_lock(2): pass
    with svc.company_lock(1): pass


def test_tenant_file_revocation_and_atomic_preflight(lab):
    with pytest.raises(ValueError): svc.publish(2,1,1,[1],'command:one')
    lab.Art.query.filter_by(id=3).one().private_path='../outside.png'; lab.db.session.commit()
    with pytest.raises(ValueError,match='private_file'): svc.publish_kit(1,1,1,'versus',1,'command:one')
    assert lab.provider.calls==[] and lab.Batch.query.count()==0
    lab.Art.query.filter_by(id=3).one().revoked_at=datetime.now(timezone.utc); lab.db.session.commit()
    with pytest.raises(ValueError,match='not_approved'): svc.publish_kit(1,1,1,'versus',1,'command:two')


def test_wrong_device_and_test_gate(lab):
    lab.provider.phone='5511999990000'
    with pytest.raises(ValueError,match='phone_mismatch'): svc.publish(1,1,1,[1],'command:one')
    lab.provider.phone='5571999991234'
    lab.Account.query.one().status_tested_at=None; lab.db.session.commit()
    with pytest.raises(ValueError,match='mobile_test'): svc.publish(1,1,1,[1],'command:one')
    assert svc.publish(1,1,1,[1],'command:test',test=True)['status']=='accepted'


def test_disabled_schedule_pause_resume_edit_review_and_restart(lab):
    row=weekly(lab); assert row['active'] is False
    now=datetime(2026,10,5,11,30,tzinfo=timezone.utc)
    svc.tick(now); assert not lab.provider.calls
    svc.set_schedule_active(1,1,1,row['id'],True)
    svc.set_schedule_active(1,1,1,row['id'],False)
    svc.tick(now); assert not lab.provider.calls
    svc.set_schedule_active(1,1,1,row['id'],True)
    lab.db.session.remove(); svc.tick(now); assert len(lab.provider.calls)==3
    lab.db.session.remove(); svc.tick(now); assert len(lab.provider.calls)==3
    assert lab.Schedule.query.one().last_result=='accepted'
    edited=svc.save_schedule(1,1,1,{'name':'Versus semanal','hour':9,'weekly_arts':{str(i):[] for i in range(7)}},row['id'])
    assert not edited['active'] and edited['revision']==2
    lab.Schedule.query.one().review_due=datetime.now(timezone.utc)-timedelta(days=1); lab.db.session.commit()
    with pytest.raises(ValueError,match='monthly_review'): svc.set_schedule_active(1,1,1,row['id'],True)
    assert svc.set_schedule_active(1,1,1,row['id'],True,reviewed=True)['active']


def test_scheduler_revocation_blocks_and_pauses(lab,monkeypatch):
    row=weekly(lab); svc.set_schedule_active(1,1,1,row['id'],True)
    monkeypatch.setattr(svc,'authorize',lambda *a: (_ for _ in ()).throw(PermissionError('revoked')))
    svc.tick(datetime(2026,10,5,11,30,tzinfo=timezone.utc))
    assert not lab.provider.calls and lab.Schedule.query.one().active is False


def test_database_rejects_cross_tenant_relationship(lab):
    from sqlalchemy.exc import IntegrityError
    batch=lab.Batch(company_id=2,command_key='command:two',payload_digest='x'*64,art_ids=[1],created_by=1,principal_id=1,status='sending')
    lab.db.session.add(batch); lab.db.session.commit()
    pub=lab.Pub(company_id=2,art_id=1,batch_id=batch.id,sha256='x'*64,local_date=datetime.now().date(),status='sending')
    lab.db.session.add(pub)
    with pytest.raises(IntegrityError): lab.db.session.commit()
    lab.db.session.rollback()


def test_pause_while_request_inflight_stops_remaining_kit(lab):
    row=weekly(lab); svc.set_schedule_active(1,1,1,row['id'],True)
    def send(data):
        lab.provider.calls.append(data)
        with lab.app.app_context():
            svc.set_schedule_active(1,1,1,row['id'],False)
        return StatusResult('accepted','provider_accepted','M1')
    lab.provider.send_image=send
    svc.tick(datetime(2026,10,5,11,30,tzinfo=timezone.utc))
    assert len(lab.provider.calls)==1
    assert lab.Batch.query.one().status=='paused'
    assert not lab.Schedule.query.one().active


def test_feature_flag_off_and_tampered_bytes_block_before_network(lab):
    lab.app.config['WHATSAPP_STATUS_ENABLED']=False
    with pytest.raises(ValueError,match='feature_disabled'): svc.publish(1,1,1,[1],'command:one')
    lab.app.config['WHATSAPP_STATUS_ENABLED']=True
    (lab.root/'1'/'1.bin').write_bytes((lab.root/'1'/'2.bin').read_bytes())
    with pytest.raises(ValueError,match='integrity_failed'): svc.publish(1,1,1,[1],'command:one')
    assert lab.provider.calls==[]


def test_restart_recovery_without_schedule_never_resends(lab):
    def crash(data): lab.provider.calls.append(data); raise SystemExit()
    lab.provider.send_image=crash
    with pytest.raises(SystemExit): svc.publish(1,1,1,[1],'command:one')
    lab.db.session.remove(); svc.tick()
    assert lab.Pub.query.one().status=='unknown' and lab.Batch.query.one().status=='unknown'
    assert len(lab.provider.calls)==1


def test_real_simultaneous_requests_have_one_sender(lab):
    from threading import Event,Thread
    started=Event(); release=Event(); results=[]
    def send(data):
        lab.provider.calls.append(data); started.set(); assert release.wait(5)
        return StatusResult('accepted','provider_accepted','M1')
    lab.provider.send_image=send
    def first():
        with lab.app.app_context():
            try: results.append(svc.publish(1,1,1,[1],'command:one'))
            except BaseException as exc: results.append(type(exc).__name__)
    thread=Thread(target=first); thread.start()
    try:
        assert started.wait(5)
        with pytest.raises(ValueError,match='busy'): svc.publish(1,1,1,[1],'command:one')
    finally:
        release.set(); thread.join(5)
    assert len(lab.provider.calls)==1 and results[0]['status']=='accepted'


def test_fixed_approved_bundle_import_is_versioned_disabled_and_idempotent(lab,monkeypatch,tmp_path):
    lab.Art.query.delete(); lab.db.session.commit()
    source=Path(__file__).resolve().parents[1]/'seeds/whatsapp_status_versus_20261007'
    stage=tmp_path/'approved'; stage.mkdir()
    import json
    manifest=json.loads((source.parent/'whatsapp_status_versus_20261007.json').read_text(encoding='utf-8'))
    for entry in manifest['arts']:
        (stage/entry['filename']).write_bytes((source/entry['filename']).read_bytes())
    lab.app.config['WHATSAPP_STATUS_APPROVED_SOURCE_ROOT']=str(stage)
    monkeypatch.setitem(sys.modules,'models.company',SimpleNamespace(Company=SimpleNamespace(query=SimpleNamespace(
        filter_by=lambda **kw:SimpleNamespace(first=lambda:SimpleNamespace(id=1) if kw.get('id')==1 else None)))))
    monkeypatch.setitem(sys.modules,'models.project',SimpleNamespace(Project=SimpleNamespace(query=SimpleNamespace(
        filter_by=lambda **kw:SimpleNamespace(first=lambda:SimpleNamespace(id=1) if kw.get('company_id')==1 else None)))))
    result=svc.register_approved_bundle(1,1,1,'versus_20261007')
    assert len(result['art_ids'])==12 and result['schedule']['active'] is False and not result['published']
    assert lab.Art.query.count()==12 and lab.Schedule.query.count()==1
    assert result['schedule']['weekly_arts']['6']==[]
    assert len(result['schedule']['weekly_arts']['4'])==2
    assert svc.register_approved_bundle(1,1,1,'versus_20261007')==result
    assert lab.Art.query.count()==12 and lab.Schedule.query.count()==1 and not lab.provider.calls
    with pytest.raises(ValueError,match='company_project'): svc.register_approved_bundle(2,1,1,'versus_20261007')
    with pytest.raises(ValueError,match='bundle_not_found'): svc.register_approved_bundle(1,1,1,'https://example.com')


def test_incomplete_kit_version_cannot_be_published(lab):
    lab.Art.query.filter_by(id=3).delete(); lab.db.session.commit()
    with pytest.raises(ValueError,match='not_approved'): svc.publish_kit(1,1,1,'versus',1,'command:one')
    assert not lab.provider.calls
