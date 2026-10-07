"""Tenant-owned Status operations. MCP adapters contain no business rules."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import base64
import re
import uuid
from flask import current_app
from sqlalchemy import text
from services.whatsapp_status_contracts import (
    BAHIA, WeeklyStatusPlan, command_key, digest, due_today, identifier, inspect_image, next_month,
)
from services.whatsapp_status_provider import ZApiStatusProvider


def _models():
    from models import db
    from models.whatsapp_status import (WhatsAppStatusAccount, WhatsAppStatusArt,
        WhatsAppStatusBatch, WhatsAppStatusPublication, WhatsAppStatusSchedule)
    return db, WhatsAppStatusAccount, WhatsAppStatusArt, WhatsAppStatusBatch, WhatsAppStatusPublication, WhatsAppStatusSchedule


def authorize(company_id, user_id, principal_id, permission):
    """Revalidated also on every scheduled execution, not a snapshot of role."""
    from models.user import User
    from models.identity_principal import IdentityPrincipal, PrincipalCompanyGrant
    from src.intelligence.security.runtime_identity import resolve_runtime_identity
    if any(type(i) is not int or i <= 0 for i in (company_id, user_id, principal_id)):
        raise PermissionError('status_identity_required')
    from models import db
    # Scheduled work must observe revoked grants/roles even in a long-lived ORM session.
    db.session.expire_all()
    user = User.query.filter_by(id=user_id).first()
    principal = IdentityPrincipal.query.filter_by(id=principal_id, user_id=user_id).first()
    grant = PrincipalCompanyGrant.query.filter_by(principal_id=principal_id, company_id=company_id, status='active').first()
    if not user or not user.is_active or not principal or not principal.is_active or not grant or not grant.is_active:
        raise PermissionError('status_identity_revoked')
    # This integration deliberately requires a narrow explicit ceiling (no * / empty).
    ceiling = grant.mcp_permissions
    allowed = {'whatsapp_status.read', 'whatsapp_status.publish', 'whatsapp_status.schedule', 'whatsapp_status.review'}
    if not isinstance(ceiling, list) or not ceiling or any(type(v) is not str or v not in allowed for v in ceiling):
        raise PermissionError('status_restricted_grant_required')
    runtime = resolve_runtime_identity(user_id=user_id, company_id=company_id)
    permissions = runtime.get('permissions') or {}
    resource, action = permission.split('.')
    if (runtime.get('role') not in ('administrador', 'admin_tecnico', 'administrador_tecnico') or
        company_id not in runtime.get('accessible_company_ids', ()) or permission not in ceiling or
        not (runtime.get('has_full_app32_permissions') or action in permissions.get(resource, []))):
        raise PermissionError('status_permission_denied')


@contextmanager
def company_lock(company_id):
    """Dedicated session lock survives ledger commits; never release through pool reset."""
    db, *_ = _models()
    if db.engine.dialect.name != 'postgresql':
        raise RuntimeError('status_requires_postgresql')
    with db.engine.connect() as conn:
        acquired = conn.execute(text('SELECT pg_try_advisory_lock(734218, :cid)'), {'cid': company_id}).scalar()
        conn.commit()
        if not acquired:
            raise ValueError('status_execution_busy')
        try:
            yield
        finally:
            db.session.rollback()
            try:
                conn.execute(text('SELECT pg_advisory_unlock(734218, :cid)'), {'cid': company_id})
                conn.commit()
            except Exception:
                conn.invalidate()


def _provider(account):
    from database.postgresql_db import get_integration
    record = get_integration(account.integration_id, company_id=account.company_id, include_global=account.allow_global)
    if not record or record.get('company_id') not in ({account.company_id, None} if account.allow_global else {account.company_id}):
        raise ValueError('status_integration_not_bound')
    if record.get('company_id') is None:
        # The legacy server-global Z-API is confirmed only for AA. Other tenants
        # must have a company-owned integration; a client bool cannot grant it.
        from models.company import Company
        if not Company.query.filter_by(id=account.company_id, client_code='AA', is_active=True).first():
            raise ValueError('status_global_integration_not_authorized')
    if str(record.get('provider')).lower() not in ('z-api', 'zapi', 'z api'):
        raise ValueError('status_provider_not_zapi')
    return ZApiStatusProvider(record.get('config') or {})


def _account(company_id, *, test=False):
    if not current_app.config.get('WHATSAPP_STATUS_ENABLED', False):
        raise ValueError('status_feature_disabled')
    db, Account, *_ = _models()
    account = Account.query.filter_by(company_id=company_id).first()
    if not account or not account.enabled or not account.verified_at:
        raise ValueError('status_account_not_verified')
    if not test and not account.status_tested_at:
        raise ValueError('status_mobile_test_required')
    return account


def verify_account(company_id, user_id, principal_id):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.review')
    db, Account, *_ = _models()
    with company_lock(company_id):
        account = Account.query.filter_by(company_id=company_id).first()
        if not account:
            raise ValueError('status_account_binding_required')
        phone = _provider(account).connected_phone()
        if phone != account.expected_phone:
            account.enabled = False
            account.verified_at = None
            db.session.commit()
            raise ValueError('status_account_phone_mismatch')
        account.verified_at = datetime.now(timezone.utc)
        # Binding enables only this service; does not touch the supplier instance.
        account.enabled = True
        db.session.commit()
        return {'phone_suffix': phone[-4:], 'account_verified': True,
                'status_mobile_test_completed': bool(account.status_tested_at)}


def bind_existing_account(company_id, user_id, principal_id, integration_id, expected_phone, *, allow_global=False):
    """Explicit server-side binding only; does not change integrations or supplier."""
    authorize(company_id, user_id, principal_id, 'whatsapp_status.review')
    if (not isinstance(integration_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', integration_id)
        or not isinstance(expected_phone, str) or not re.fullmatch(r'\d{10,15}', expected_phone)
        or type(allow_global) is not bool):
        raise ValueError('status_account_binding_invalid')
    db, Account, *_ = _models()
    with company_lock(company_id):
        row = Account.query.filter_by(company_id=company_id).first()
        if row and (row.integration_id, row.expected_phone, row.allow_global) == (integration_id, expected_phone, allow_global):
            return {'bound': True, 'reused': True}
        if row and row.enabled:
            raise ValueError('status_account_binding_already_enabled')
        if not row:
            row = Account(company_id=company_id)
            db.session.add(row)
        row.integration_id = integration_id; row.expected_phone = expected_phone; row.allow_global = allow_global
        _provider(row)  # validates owner and provider without a network mutation
        row.enabled = False; row.verified_at = None; row.status_tested_at = None
        db.session.commit()
        return {'bound': True, 'reused': False}


def _art(company_id, art_id):
    if type(art_id) is not int or art_id <= 0:
        raise ValueError('invalid_art_id')
    _, _, Art, *_ = _models()
    art = Art.query.filter_by(company_id=company_id, id=art_id, revoked_at=None).first()
    if not art:
        raise ValueError('status_approved_art_not_found')
    return art


def _root(company_id):
    return Path(current_app.config.get('WHATSAPP_STATUS_PRIVATE_ROOT',
                Path(current_app.instance_path) / 'whatsapp_status')).resolve() / str(company_id)


def _bytes(art):
    root = _root(art.company_id).resolve()
    path = (root / art.private_path).resolve()
    if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
        raise ValueError('status_private_file_invalid')
    from services.whatsapp_status_contracts import MAX_IMAGE_BYTES
    with path.open('rb') as stream:
        data = stream.read(MAX_IMAGE_BYTES + 1)
    sha, mime = inspect_image(data)
    if sha != art.sha256 or mime != art.mime:
        raise ValueError('status_art_integrity_failed')
    return data


def import_approved_art(*, company_id, user_id, principal_id, project_id, kit_code,
                        code, version, position, kit_size, data):
    """Administrative server-side ingestion. Not an MCP arbitrary file/URL tool."""
    authorize(company_id, user_id, principal_id, 'whatsapp_status.review')
    from models.project import Project
    if not Project.query.filter_by(company_id=company_id, id=project_id, is_deleted=False).first():
        raise ValueError('status_project_not_found')
    identifier(kit_code); identifier(code)
    if any(type(i) is not int or i < 1 for i in (version, position, kit_size)) or not position <= kit_size <= 12:
        raise ValueError('status_art_version_or_order_invalid')
    sha, mime = inspect_image(data)
    db, _, Art, *_ = _models()
    with company_lock(company_id):
        old = Art.query.filter_by(company_id=company_id, code=code, version=version).first()
        if old:
            if (old.sha256, old.kit_code, old.position, old.project_id, old.kit_size) != (sha, kit_code, position, project_id, kit_size):
                raise ValueError('status_immutable_version_conflict')
            return {'art_id': old.id, 'reused': True}
        root = _root(company_id)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        filename = f'{uuid.uuid4().hex}.bin'
        with (root / filename).open('xb') as target:
            target.write(data)
        (root / filename).chmod(0o600)
        art = Art(company_id=company_id, project_id=project_id, kit_code=kit_code, code=code,
                  version=version, position=position, kit_size=kit_size, private_path=filename, sha256=sha,
                  mime=mime, approved_by=user_id)
        db.session.add(art)
        db.session.commit()
        return {'art_id': art.id, 'sha256': sha, 'reused': False}


def list_arts(company_id, user_id, principal_id):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.read')
    _, _, Art, *_ = _models()
    rows = Art.query.filter_by(company_id=company_id, revoked_at=None).order_by(Art.kit_code, Art.version, Art.position).all()
    return {'arts': [{'id': a.id, 'kit': a.kit_code, 'code': a.code, 'version': a.version,
                     'position': a.position, 'sha256': a.sha256} for a in rows]}


def inspect_setup(company_id, user_id, principal_id):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.read')
    from models.integration_request import IntegrationRequest
    from database.postgresql_db import list_integrations
    db, Account, *_ = _models()
    account = Account.query.filter_by(company_id=company_id).first()
    requests = IntegrationRequest.query.filter(IntegrationRequest.company_id == company_id,
        (IntegrationRequest.external_system.ilike('%z%api%') | IntegrationRequest.external_system.ilike('%whatsapp%')
         | IntegrationRequest.title.ilike('%whatsapp%') | IntegrationRequest.title.ilike('%status%')
         | IntegrationRequest.title.ilike('%mcp%'))).all()
    references = list_integrations(company_id=company_id) or []
    return {'account_bound': bool(account), 'account_verified': bool(account and account.verified_at),
            'mobile_test_confirmed': bool(account and account.status_tested_at),
            'phone_suffix': account.expected_phone[-4:] if account else None,
            'existing_requests': [{'id': r.id, 'status': r.status} for r in requests],
            'integration_references': [{'id': r['id'], 'global': r.get('company_id') is None}
                for r in references if r.get('company_id') in (None, company_id)
                and str(r.get('provider')).lower() in ('z-api', 'zapi', 'z api')]}


def register_approved_bundle(company_id, user_id, principal_id, bundle_code):
    """Fixed reviewed bundle; server config selects source, never an arbitrary client URL/path."""
    authorize(company_id, user_id, principal_id, 'whatsapp_status.review')
    authorize(company_id, user_id, principal_id, 'whatsapp_status.schedule')
    if bundle_code != 'versus_20261007':
        raise ValueError('status_approved_bundle_not_found')
    from models.company import Company
    from models.project import Project
    import json
    company = Company.query.filter_by(id=company_id, client_code='AA', is_active=True).first()
    # Marketing Digital: database ID 187, canonical code AA.J.26 (not AA.J.187).
    project = Project.query.filter_by(company_id=company_id, id=187, code_sequence=26, is_deleted=False).first()
    if not company or not project:
        raise ValueError('status_bundle_company_project_mismatch')
    app_root = Path(__file__).resolve().parents[1]
    manifest = json.loads((app_root / 'seeds' / 'whatsapp_status_versus_20261007.json').read_text(encoding='utf-8'))
    source_config = current_app.config.get('WHATSAPP_STATUS_APPROVED_SOURCE_ROOT')
    if not source_config:
        raise ValueError('status_approved_source_not_staged')
    source = Path(source_config).resolve()
    entries = manifest['arts']
    data_by_code = {}
    # Whole bundle verification first, including all pinned hashes.
    for entry in entries:
        path = (source / entry['filename']).resolve()
        if not path.is_relative_to(source):
            raise ValueError('status_bundle_path_invalid')
        from services.whatsapp_status_contracts import MAX_IMAGE_BYTES
        with path.open('rb') as stream:
            data = stream.read(MAX_IMAGE_BYTES + 1)
        if inspect_image(data) != (entry['sha256'], entry['mime']):
            raise ValueError('status_bundle_hash_mismatch')
        data_by_code[entry['code']] = data
    arts = {}
    for entry in entries:
        result = import_approved_art(company_id=company_id, user_id=user_id, principal_id=principal_id,
            project_id=project.id, kit_code=entry['kit_code'], code=entry['code'], version=entry['version'],
            position=entry['position'], kit_size=sum(e['kit_code']==entry['kit_code'] for e in entries),
            data=data_by_code[entry['code']])
        arts[entry['code']] = result['art_id']
    _, _, _, _, _, Schedule = _models()
    existing = Schedule.query.filter_by(company_id=company_id, name='Versus semanal').first()
    if existing:
        schedule = _schedule_dict(existing)  # Never reset or activate an existing agenda.
    else:
        schedule = save_schedule(company_id, user_id, principal_id, {
            'name': 'Versus semanal', 'hour': 8, 'minute': 30, 'timezone': 'America/Bahia',
            'weekly_arts': {day: [arts[code] for code in codes] for day, codes in manifest['weekly_codes'].items()},
        })
    return {'art_ids': arts, 'schedule': schedule, 'published': False}


def _batch_dict(batch):
    _, _, _, _, Pub, _ = _models()
    pubs = Pub.query.filter_by(company_id=batch.company_id, batch_id=batch.id).order_by(Pub.id).all()
    return {'batch_id': batch.id, 'status': batch.status, 'art_ids': batch.art_ids,
            'results': [{'id': p.id, 'art_id': p.art_id, 'status': p.status, 'code': p.result_code,
                         'mobile_confirmed': bool(p.mobile_confirmed_at)} for p in pubs]}


def _publish_locked(company_id, user_id, principal_id, art_ids, key, *, schedule=None, test=False):
    db, _, _, Batch, Pub, _ = _models()
    authorize(company_id, user_id, principal_id, 'whatsapp_status.publish')
    command_key(key)
    if not isinstance(art_ids, list) or not 1 <= len(art_ids) <= 12 or len(set(art_ids)) != len(art_ids):
        raise ValueError('status_invalid_art_list')
    arts = [_art(company_id, i) for i in art_ids]
    account = _account(company_id, test=test)
    prior = Batch.query.filter_by(company_id=company_id, command_key=key).first()
    if prior:
        if prior.payload_digest != digest(art_ids):
            raise ValueError('status_command_payload_conflict')
        # Interrupted work never resumes automatically, even if provider accepted.
        if prior.status == 'sending':
            for p in Pub.query.filter_by(company_id=company_id, batch_id=prior.id, status='sending').all():
                p.status = 'unknown'; p.result_code = 'process_interrupted'
            prior.status = 'unknown'
            db.session.commit()
        return _batch_dict(prior)
    # Preflight the WHOLE kit before first side effect.
    images = [_bytes(a) for a in arts]
    if len({a.sha256 for a in arts}) != len(arts):
        raise ValueError('status_duplicate_image_in_kit')
    local_date = datetime.now(timezone.utc).astimezone(BAHIA).date()
    if Pub.query.filter(Pub.company_id == company_id, Pub.sha256.in_([a.sha256 for a in arts]), Pub.local_date == local_date).first():
        raise ValueError('status_daily_duplicate_blocked')
    provider = _provider(account)
    # Verify number again immediately before every batch to avoid device drift.
    if provider.connected_phone() != account.expected_phone:
        raise ValueError('status_account_phone_mismatch')
    batch = Batch(company_id=company_id, command_key=key, payload_digest=digest(art_ids), art_ids=art_ids,
                  created_by=user_id, principal_id=principal_id, schedule_id=getattr(schedule, 'id', None), status='sending')
    db.session.add(batch); db.session.commit()
    for art, image in zip(arts, images):
        if schedule is not None:
            db.session.refresh(schedule)
            if not schedule.active:
                batch.status = 'paused'; db.session.commit()
                return _batch_dict(batch)
        authorize(company_id, user_id, principal_id, 'whatsapp_status.publish')
        _art(company_id, art.id)  # approval can be revoked while a batch is running
        pub = Pub(company_id=company_id, art_id=art.id, batch_id=batch.id, sha256=art.sha256,
                  local_date=local_date, status='sending')
        db.session.add(pub); db.session.commit()  # durable BEFORE the request
        result = provider.send_image('data:' + art.mime + ';base64,' + base64.b64encode(image).decode('ascii'))
        pub.status = result.status; pub.result_code = result.code
        pub.provider_message_id = result.message_id; pub.finished_at = datetime.now(timezone.utc)
        if result.status != 'accepted':
            batch.status = result.status
            db.session.commit()
            return _batch_dict(batch)
        db.session.commit()
    batch.status = 'accepted'; db.session.commit()
    return _batch_dict(batch)


def publish(company_id, user_id, principal_id, art_ids, key, *, test=False):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.publish')
    with company_lock(company_id):
        return _publish_locked(company_id, user_id, principal_id, art_ids, key, test=test)


def publish_kit(company_id, user_id, principal_id, kit_code, version, key):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.publish')
    identifier(kit_code)
    if type(version) is not int or version < 1:
        raise ValueError('invalid_kit_version')
    _, _, Art, *_ = _models()
    with company_lock(company_id):
        arts = Art.query.filter_by(company_id=company_id, kit_code=kit_code, version=version).order_by(Art.position).all()
        if (not arts or any(a.revoked_at or a.kit_size != len(arts) for a in arts)
            or [a.position for a in arts] != list(range(1, len(arts)+1))):
            raise ValueError('status_kit_not_approved')
        return _publish_locked(company_id, user_id, principal_id, [a.id for a in arts], key)


def _schedule_dict(row):
    return {'id': row.id, 'name': row.name, 'active': row.active, 'timezone': row.timezone,
            'hour': row.hour, 'minute': row.minute, 'weekly_arts': row.weekly_arts,
            'revision': row.revision, 'review_due': row.review_due.isoformat(), 'last_result': row.last_result}


def save_schedule(company_id, user_id, principal_id, plan, schedule_id=None):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.schedule')
    try:
        plan = WeeklyStatusPlan.model_validate(plan).checked()
    except Exception:
        raise ValueError('status_schedule_payload_invalid') from None
    db, _, _, _, _, Schedule = _models()
    with company_lock(company_id):
        for ids in plan.weekly_arts.values():
            for i in ids:
                _art(company_id, i)
        row = Schedule.query.filter_by(company_id=company_id, id=schedule_id).first() if schedule_id else None
        if schedule_id and not row:
            raise ValueError('status_schedule_not_found')
        if not row:
            row = Schedule(company_id=company_id, created_by=user_id, principal_id=principal_id,
                           active=False, revision=0, review_due=next_month(datetime.now(timezone.utc)))
            db.session.add(row)
        # Changes always pause. Resume is separately authorized/confirmed.
        row.active = False; row.revision += 1
        for field in ('name', 'hour', 'minute', 'timezone', 'weekly_arts'):
            setattr(row, field, getattr(plan, field))
        db.session.commit()
        return _schedule_dict(row)


def set_schedule_active(company_id, user_id, principal_id, schedule_id, active, *, reviewed=False):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.schedule')
    db, _, _, _, _, Schedule = _models()
    # Safety stop must not wait for provider I/O. In-flight request cannot be
    # recalled; the publication loop observes this flag before the next art.
    if active is False:
        row = Schedule.query.filter_by(company_id=company_id, id=schedule_id).first()
        if not row:
            raise ValueError('status_schedule_not_found')
        row.active = False; db.session.commit()
        return _schedule_dict(row)
    with company_lock(company_id):
        row = Schedule.query.filter_by(company_id=company_id, id=schedule_id).first()
        if not row:
            raise ValueError('status_schedule_not_found')
        if active:
            authorize(company_id, user_id, principal_id, 'whatsapp_status.publish')
            _account(company_id)
            if reviewed:
                authorize(company_id, user_id, principal_id, 'whatsapp_status.review')
                row.review_due = next_month(datetime.now(timezone.utc))
            if row.review_due <= datetime.now(timezone.utc):
                raise ValueError('status_monthly_review_required')
            row.created_by = user_id; row.principal_id = principal_id
        row.active = active
        db.session.commit()
        return _schedule_dict(row)


def list_schedules(company_id, user_id, principal_id):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.read')
    *_, Schedule = _models()
    return {'schedules': [_schedule_dict(s) for s in Schedule.query.filter_by(company_id=company_id).order_by(Schedule.id).all()]}


def list_results(company_id, user_id, principal_id, limit=30):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.read')
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('status_invalid_limit')
    _, _, _, Batch, *_ = _models()
    return {'batches': [_batch_dict(b) for b in Batch.query.filter_by(company_id=company_id).order_by(Batch.id.desc()).limit(limit).all()]}


def confirm_mobile(company_id, user_id, principal_id, publication_id):
    authorize(company_id, user_id, principal_id, 'whatsapp_status.review')
    db, Account, _, _, Pub, _ = _models()
    with company_lock(company_id):
        pub = Pub.query.filter_by(company_id=company_id, id=publication_id, status='accepted').first()
        if not pub:
            raise ValueError('status_accepted_publication_not_found')
        pub.mobile_confirmed_at = datetime.now(timezone.utc); pub.mobile_confirmed_by = user_id
        account = Account.query.filter_by(company_id=company_id).first()
        account.status_tested_at = pub.mobile_confirmed_at
        db.session.commit()
        return {'publication_id': pub.id, 'mobile_confirmed': True}


def tick(now=None):
    """Server runtime only. Enumerate tenants, then every read/write is tenant-scoped."""
    db, _, _, Batch, Pub, Schedule = _models()
    now = now or datetime.now(timezone.utc)
    companies = {r[0] for r in db.session.query(Schedule.company_id).distinct().all()}
    companies.update(r[0] for r in db.session.query(Batch.company_id).filter_by(status='sending').distinct().all())
    for company_id in companies:
        try:
            with company_lock(company_id):
                # Crash recovery records uncertainty but NEVER sends again.
                for pub in Pub.query.filter_by(company_id=company_id, status='sending').all():
                    pub.status = 'unknown'; pub.result_code = 'process_interrupted'
                for batch in Batch.query.filter_by(company_id=company_id, status='sending').all():
                    batch.status = 'unknown'
                    if batch.schedule_id:
                        schedule = Schedule.query.filter_by(company_id=company_id, id=batch.schedule_id).first()
                        if schedule:
                            schedule.active = False; schedule.last_result = 'process_interrupted'
                db.session.commit()
                for row in Schedule.query.filter_by(company_id=company_id, active=True).all():
                    if row.review_due <= now:
                        row.active = False; row.last_result = 'monthly_review_required'; db.session.commit(); continue
                    plan = WeeklyStatusPlan(name=row.name, hour=row.hour, minute=row.minute,
                                            timezone=row.timezone, weekly_arts=row.weekly_arts).checked()
                    if not due_today(plan, now, row.last_run_date):
                        continue
                    day = now.astimezone(BAHIA).date()
                    # Claim date before dispatch. Restart can't regenerate this occurrence.
                    row.last_run_date = day; row.last_result = 'claimed'; db.session.commit()
                    try:
                        authorize(company_id, row.created_by, row.principal_id, 'whatsapp_status.schedule')
                        result = _publish_locked(company_id, row.created_by, row.principal_id,
                            plan.weekly_arts[str(now.astimezone(BAHIA).weekday())], f'schedule:{row.id}:{day}', schedule=row)
                        row.last_result = result['status']
                        if result['status'] != 'accepted':
                            row.active = False
                    except Exception:
                        db.session.rollback()
                        row.last_result = 'blocked_or_uncertain'; row.active = False
                    db.session.commit()
        except ValueError:
            db.session.rollback()  # busy: next minute; no resend of committed occurrences
