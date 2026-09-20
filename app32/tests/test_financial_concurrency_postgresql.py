"""Opt-in, real service/model/transaction tests; disposable local PostgreSQL only."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier, local
import time

import pytest
from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import make_url

from models import Company, db
from models.financial import (FinancialBankAccount, FinancialEntry, FinancialSettlement,
                              FinancialSchedule, FinancialBordero, FinancialBorderoItem,
                              FinancialBorderoSettlement)
from services.financial_service import FinancialService
from services.financial_bordero_service import FinancialBorderoService


@pytest.fixture(scope='module')
def lab():
    raw = os.environ.get('APP32_FINANCIAL_LAB_URL')
    if not raw:
        pytest.skip('Disposable financial lab not configured')
    url = make_url(raw)
    assert url.get_backend_name() == 'postgresql'
    assert url.host == '127.0.0.1' and url.database == 'app32_financial_concurrency_lab'
    app = Flask('financial-concurrency-lab')
    app.config.update(SQLALCHEMY_DATABASE_URI=raw, SQLALCHEMY_TRACK_MODIFICATIONS=False,
                      SQLALCHEMY_ENGINE_OPTIONS={'pool_size': 4, 'max_overflow': 0,
                          'connect_args': {'options': '-c statement_timeout=12000 -c lock_timeout=6000'}})
    db.init_app(app)
    with app.app_context():
        # Model-defined schema, not a validation of production migration history.
        tables = {table for name, table in db.metadata.tables.items() if name.startswith('financial_')}
        pending = list(tables)
        while pending:
            for foreign_key in pending.pop().foreign_keys:
                dependency = foreign_key.column.table
                if dependency not in tables:
                    tables.add(dependency)
                    pending.append(dependency)
        db.metadata.create_all(db.engine, tables=list(tables))
        a = Company(name='SYNTHETIC A')
        b = Company(name='SYNTHETIC B')
        db.session.add_all([a, b])
        db.session.flush()
        bank = FinancialBankAccount(company_id=b.id, code='B', name='Synthetic B bank')
        db.session.add(bank)
        db.session.commit()
        ids = (a.id, b.id, bank.id)
    yield app, ids
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def new_entry(app, company, code):
    with app.app_context():
        entry = FinancialEntry(company_id=company, entry_code=code, entry_type='receivable',
                               movement_nature='credit', status='posted', description='SYNTHETIC',
                               competence_date=date(2026, 9, 20), original_amount=Decimal('100'))
        db.session.add(entry)
        db.session.commit()
        return entry.id


def settle(app, company, entry, code, **extra):
    with app.app_context():
        backend_pid = db.session.execute(db.text('select pg_backend_pid()')).scalar()
        result, error = FinancialService.create_settlement(payload={
            'company_id': company, 'financial_entry_id': entry, 'settlement_code': code,
            'settlement_type': 'manual', 'settlement_date': date(2026, 9, 20),
            'principal_amount': Decimal('60'), **extra}, allowed_company_ids=[company])
        return {'id': result.id if result else None, 'error': error, 'backend_pid': backend_pid}


def total(app, entry):
    with app.app_context():
        return db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0)).filter(
            FinancialSettlement.financial_entry_id == entry).scalar()


def test_sequential_overpayment_is_rejected(lab):
    app, (a, _, _) = lab
    entry = new_entry(app, a, 'SEQ')
    first = settle(app, a, entry, 'SEQ-A')
    second = settle(app, a, entry, 'SEQ-B')
    assert first['id'], first
    assert second['id'] is None and 'excede' in second['error'], second
    assert total(app, entry) == Decimal('60')


def test_cross_company_entry_and_bank_are_rejected(lab):
    app, (a, b, bank_b) = lab
    entry = new_entry(app, a, 'TENANT')
    wrong_entry = settle(app, b, entry, 'DENY-ENTRY')
    wrong_bank = settle(app, a, entry, 'DENY-BANK', bank_account_id=bank_b)
    assert wrong_entry['id'] is None and wrong_entry['error'], wrong_entry
    assert wrong_bank['id'] is None and wrong_bank['error'], wrong_bank
    assert total(app, entry) == 0


def test_concurrent_settlements_must_not_exceed_principal(lab):
    app, (a, _, _) = lab
    entry = new_entry(app, a, 'RACE')
    barrier = Barrier(2, timeout=8)
    seen = local()
    def synchronize_entry_lock(conn, cursor, statement, parameters, context, executemany):
        # Both clients reach the entry query before either tries to take the lock.
        sql = statement.lower()
        if not getattr(seen, 'done', False) and sql.startswith('select') and 'from financial_entries' in sql:
            seen.done = True
            barrier.wait()
    def hold_validation_window(conn, cursor, statement, parameters, context, executemany):
        if 'sum(financial_settlements.principal_amount)' in statement.lower():
            time.sleep(.2)
    with app.app_context():
        engine = db.engine
    event.listen(engine, 'before_cursor_execute', synchronize_entry_lock)
    event.listen(engine, 'after_cursor_execute', hold_validation_window)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(settle, app, a, entry, f'RACE-{n}') for n in (1, 2)]
            outcomes = [future.result(timeout=20) for future in futures]
    finally:
        event.remove(engine, 'before_cursor_execute', synchronize_entry_lock)
        event.remove(engine, 'after_cursor_execute', hold_validation_window)
    amount = total(app, entry)
    assert len({row['backend_pid'] for row in outcomes}) == 2, outcomes
    assert amount <= Decimal('100'), f'OVERPAYMENT: total={amount}; outcomes={outcomes}'
    assert sum(row['id'] is not None for row in outcomes) == 1, outcomes


def test_concurrent_auto_codes_on_distinct_entries_are_unique(lab):
    app, (a, _, _) = lab
    entries = [new_entry(app, a, 'AUTO-CODE-' + str(i)) for i in range(2)]
    barrier = Barrier(2, timeout=8)
    def synchronize_insert(conn, cursor, statement, parameters, context, executemany):
        if 'pg_try_advisory_xact_lock' in statement:
            barrier.wait()
    def hold_numbering_window(conn, cursor, statement, parameters, context, executemany):
        if 'pg_try_advisory_xact_lock' in statement:
            time.sleep(0.2)
    with app.app_context():
        engine = db.engine
    event.listen(engine, 'before_cursor_execute', synchronize_insert)
    event.listen(engine, 'after_cursor_execute', hold_numbering_window)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda entry: settle(app, a, entry, None), entries))
    finally:
        event.remove(engine, 'before_cursor_execute', synchronize_insert)
        event.remove(engine, 'after_cursor_execute', hold_numbering_window)
    assert len({row['backend_pid'] for row in outcomes}) == 2
    assert sum(bool(row['id']) for row in outcomes) == 1, outcomes
    for entry, row in zip(entries, outcomes):
        if not row['id']:
            assert 'Numeração de baixas em processamento' in row['error'], row
            assert total(app, entry) == 0
            assert settle(app, a, entry, None)['id']
    with app.app_context():
        rows = FinancialSettlement.query.filter(FinancialSettlement.company_id == a,
            FinancialSettlement.financial_entry_id.in_(entries)).all()
        assert len(rows) == 2 and len({row.settlement_code for row in rows}) == 2
    assert all(total(app, entry) == Decimal('60') for entry in entries)


def test_numbering_lock_is_tenant_scoped_fast_and_released(lab):
    app, (a, b, _) = lab
    first = new_entry(app, a, 'NUMBER-LOCK-A')
    other = new_entry(app, b, 'NUMBER-LOCK-B')
    manual = new_entry(app, a, 'NUMBER-MANUAL')
    with app.app_context():
        engine = db.engine
    with engine.begin() as owner:
        owner.execute(db.text('SELECT pg_advisory_xact_lock(:ns, :company)'),
            {'ns': 1735816302, 'company': a})
        start = time.monotonic()
        rejected = settle(app, a, first, None)
        assert not rejected['id'] and 'Numeração' in rejected['error']
        assert time.monotonic() - start < 2
        assert settle(app, b, other, None)['id']
        assert settle(app, a, manual, 'MANUAL-UNCHANGED')['id']
    assert settle(app, a, first, None)['id']


@pytest.mark.parametrize('rejection', ['missing_entry', 'overpayment'])
def test_rejected_auto_settlement_releases_numbering_before_request_teardown(lab, rejection):
    app, (a, _, _) = lab
    entry = new_entry(app, a, 'RELEASE-' + rejection)
    with app.app_context():
        result, error = FinancialService.create_settlement(payload={
            'company_id': a, 'financial_entry_id': -1 if rejection == 'missing_entry' else entry,
            'settlement_type': 'manual', 'settlement_date': date(2026, 9, 20),
            'principal_amount': Decimal('101')}, allowed_company_ids=[a])
        assert result is None and error
        # Keep the rejected request's Flask session alive; another connection
        # must already be able to acquire the company numbering lock.
        with db.engine.begin() as other:
            acquired = other.execute(db.text('SELECT pg_try_advisory_xact_lock(:ns, :company)'),
                {'ns': 1735816302, 'company': a}).scalar()
            assert acquired, 'Rejected settlement retained company numbering lock'
    assert total(app, entry) == 0


def test_locked_entry_fails_fast_and_other_entry_is_not_blocked(lab):
    app, (a, _, _) = lab
    locked = new_entry(app, a, 'LOCKED')
    other = new_entry(app, a, 'INDEPENDENT')
    with app.app_context():
        engine = db.engine
    with engine.begin() as owner:
        owner.execute(db.text('SELECT id FROM financial_entries WHERE id=:id AND company_id=:company FOR UPDATE'),
                      {'id': locked, 'company': a})
        start = time.monotonic()
        rejected = settle(app, a, locked, 'LOCK-REJECT')
        elapsed = time.monotonic() - start
        assert rejected['id'] is None and 'em processamento' in rejected['error'], rejected
        assert elapsed < 2, elapsed
        independent = settle(app, a, other, 'LOCK-OTHER')
        assert independent['id'], independent
        assert total(app, locked) == 0
    recovered = settle(app, a, locked, 'LOCK-RECOVER')
    assert recovered['id'], recovered
    assert total(app, locked) == Decimal('60')


def test_lock_refreshes_entry_already_present_in_session(lab):
    app, (a, _, _) = lab
    entry_id = new_entry(app, a, 'REFRESH')
    with app.app_context():
        cached = db.session.get(FinancialEntry, entry_id)
        assert cached.original_amount == Decimal('100')
        with db.engine.begin() as conn:
            conn.execute(db.text('UPDATE financial_entries SET original_amount=40 WHERE id=:id'), {'id': entry_id})
        result, error = FinancialService.create_settlement(payload={
            'company_id': a, 'financial_entry_id': entry_id, 'settlement_code': 'REFRESH-REJECT',
            'settlement_type': 'manual', 'settlement_date': date(2026, 9, 20),
            'principal_amount': Decimal('60')}, allowed_company_ids=[a])
        assert result is None and 'excede' in error
        assert cached.original_amount == Decimal('40')
    assert total(app, entry_id) == 0


def seed_bordero_reversal(app, company, code):
    """Persist a two-item bordero with two child settlements; second is reconciled."""
    with app.app_context():
        bordero = FinancialBordero(company_id=company, bordero_code=code, name='SYNTHETIC',
            description='SYNTHETIC', bordero_type='receivable', status='partially_settled',
            total_amount=200, settled_amount=120, open_amount=80)
        db.session.add(bordero)
        db.session.flush()
        parent = FinancialBorderoSettlement(company_id=company, bordero_id=bordero.id,
            settlement_code=code+'-BX', settlement_date=date(2026, 9, 20),
            gross_amount=120, allocated_amount=120)
        db.session.add(parent)
        db.session.flush()
        children = []
        for n in (1, 2):
            schedule = FinancialSchedule(company_id=company, schedule_code=f'{code}-T{n}',
                name='SYNTHETIC', description='SYNTHETIC', entry_type='receivable',
                movement_nature='credit', frequency='one_time', status='active',
                start_date=date(2026, 9, 20), competence_date=date(2026, 9, 20),
                first_due_date=date(2026, 9, 20), next_due_date=date(2026, 9, 20), template_amount=100)
            db.session.add(schedule)
            db.session.flush()
            entry = FinancialEntry(company_id=company, entry_code=f'{code}-E{n}',
                financial_schedule_id=schedule.id, entry_type='receivable', movement_nature='credit',
                status='partially_settled', description='SYNTHETIC',
                competence_date=date(2026, 9, 20), original_amount=100)
            db.session.add(entry)
            db.session.flush()
            db.session.add(FinancialBorderoItem(company_id=company, bordero_id=bordero.id,
                financial_schedule_id=schedule.id, item_code=f'{code}-I{n}',
                selected_amount=100, settled_amount=60, open_amount=40, display_order=n))
            child = FinancialSettlement(company_id=company, financial_entry_id=entry.id,
                settlement_code=f'{code}-C{n}', settlement_type='manual',
                settlement_date=date(2026, 9, 20), principal_amount=60, gross_amount=60, net_amount=60,
                reconciliation_status='reconciled' if n == 2 else 'pending',
                external_reference=parent.settlement_code,
                metadata_json={'reconcile_via_bordero': True, 'bordero_id': bordero.id,
                               'bordero_settlement_id': parent.id, 'bordero_settlement_code': parent.settlement_code})
            db.session.add(child)
            db.session.flush()
            children.append(child.id)
        db.session.commit()
        return bordero.id, parent.id, children


def test_bordero_reversal_denies_wrong_company_without_changes(lab):
    app, (a, b, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'REV-TENANT')
    with app.app_context():
        result, error = FinancialBorderoService.delete_settlement(bordero_id=bordero,
            settlement_id=parent, company_id=b, allowed_company_ids=[b])
        assert result is None and error
    with app.app_context():
        assert all(db.session.get(FinancialSettlement, key).deleted_at is None for key in children)


def test_bordero_reversal_failure_must_rollback_all_children(lab):
    app, (a, _, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'REV-ATOMIC')
    with app.app_context():
        result, error = FinancialBorderoService.delete_settlement(bordero_id=bordero,
            settlement_id=parent, company_id=a, allowed_company_ids=[a])
        assert result is None and 'conciliada' in error, (result, error)
        # Even an explicit outer rollback must undo the entire failed operation.
        db.session.rollback()
    with app.app_context():
        deleted = [key for key in children if db.session.get(FinancialSettlement, key).deleted_at is not None]
        parent_deleted = db.session.get(FinancialBorderoSettlement, parent).deleted_at
        assert not deleted and parent_deleted is None, f'PARTIAL_REVERSAL: child_ids={deleted}, parent_deleted={parent_deleted}'


def test_reversal_of_locked_entry_must_fail_fast(lab):
    app, (a, _, _) = lab
    entry = new_entry(app, a, 'REV-LOCKED')
    created = settle(app, a, entry, 'REV-LOCKED-BX')
    assert created['id'], created
    with app.app_context():
        engine = db.engine
    with engine.begin() as owner:
        owner.execute(db.text('SELECT id FROM financial_entries WHERE id=:id FOR UPDATE'), {'id': entry})
        with app.app_context():
            start = time.monotonic()
            result, error = FinancialService.delete_settlement(settlement_id=created['id'],
                company_id=a, allowed_company_ids=[a])
            elapsed = time.monotonic() - start
            assert result is None and error
            assert elapsed < 2, f'Reversal waited {elapsed:.2f}s behind entry lock'
    with app.app_context():
        assert db.session.get(FinancialSettlement, created['id']).deleted_at is None


def test_bordero_reversal_success_commits_once_and_reopens_all_items(lab):
    app, (a, _, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'REV-SUCCESS')
    with app.app_context():
        db.session.get(FinancialSettlement, children[1]).reconciliation_status = 'pending'
        db.session.commit()
        engine = db.engine
    commits = []
    def committed(conn):
        commits.append(True)
    event.listen(engine, 'commit', committed)
    try:
        with app.app_context():
            result, error = FinancialBorderoService.delete_settlement(bordero_id=bordero,
                settlement_id=parent, company_id=a, allowed_company_ids=[a])
            assert result is not None and error is None, error
    finally:
        event.remove(engine, 'commit', committed)
    assert len(commits) == 1, commits
    with app.app_context():
        assert all(db.session.get(FinancialSettlement, key).deleted_at is not None for key in children)
        assert db.session.get(FinancialBorderoSettlement, parent).settlement_status == 'cancelled'
        saved = db.session.get(FinancialBordero, bordero)
        assert saved.open_amount == Decimal('200') and saved.settled_amount == 0
        assert all(item.open_amount == Decimal('100') for item in saved.items.all())


def test_bordero_reversal_lock_conflict_changes_nothing(lab):
    app, (a, _, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'REV-PARENT-LOCK')
    with app.app_context():
        engine = db.engine
    with engine.begin() as owner:
        owner.execute(db.text('SELECT id FROM financial_borderos WHERE id=:id FOR UPDATE'), {'id': bordero})
        with app.app_context():
            start = time.monotonic()
            result, error = FinancialBorderoService.delete_settlement(bordero_id=bordero,
                settlement_id=parent, company_id=a, allowed_company_ids=[a])
            assert result is None and 'em processamento' in error, error
            assert time.monotonic() - start < 2
    with app.app_context():
        assert all(db.session.get(FinancialSettlement, key).deleted_at is None for key in children)
        assert db.session.get(FinancialBorderoSettlement, parent).deleted_at is None


@pytest.mark.parametrize('operation', ['create', 'edit', 'satellite_failure', 'real_policy_failure'])
def test_bordero_success_commits_once_with_consistent_balances(lab, operation, monkeypatch, caplog):
    app, (a, _, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'SUCCESS-' + operation)
    with app.app_context():
        if operation == 'real_policy_failure':
            from models.financial import FinancialSatellitePolicy, FinancialScheduleLink
            schedules = [db.session.get(FinancialEntry,
                db.session.get(FinancialSettlement, key).financial_entry_id).financial_schedule_id for key in children]
            policy = FinancialSatellitePolicy(company_id=a, policy_code='REAL-POLICY',
                name='SYNTHETIC proportional retention', satellite_nature='iss_withheld',
                principal_effect_mode='partial_settlement_by_settlement',
                satellite_effect_mode='settle_by_settlement', trigger_event='on_partial_settlement',
                settlement_scope='proportional', auto_apply=True)
            db.session.add(policy)
            db.session.flush()
            policy_id = policy.id
            db.session.add(FinancialScheduleLink(company_id=a, parent_schedule_id=schedules[0],
                child_schedule_id=schedules[1], policy_id=policy.id, title_nature='iss_withheld'))
        if operation != 'edit':
            for key in children:
                db.session.delete(db.session.get(FinancialSettlement, key))
            db.session.delete(db.session.get(FinancialBorderoSettlement, parent))
            saved = db.session.get(FinancialBordero, bordero)
            saved.settled_amount, saved.open_amount, saved.status = 0, 200, 'open'
            for item in saved.items.all():
                item.settled_amount, item.open_amount = 0, 100
        else:
            db.session.get(FinancialSettlement, children[1]).reconciliation_status = 'pending'
        db.session.commit()
        engine = db.engine
    commits = []
    if operation == 'satellite_failure':
        from services.contract_financial_service import ContractFinancialService
        def fail_satellite(**kwargs):
            # Application exception, deliberately without a database rollback.
            raise RuntimeError('SYNTHETIC satellite failure')
        monkeypatch.setattr(ContractFinancialService, 'handle_schedule_settlement_event', fail_satellite)
    def committed(conn):
        commits.append(True)
    event.listen(engine, 'commit', committed)
    try:
        with app.app_context():
            if operation != 'edit':
                result, error = FinancialBorderoService.create_settlement(bordero_id=bordero,
                    payload={'company_id': a, 'gross_amount': 100, 'settlement_date': date(2026, 9, 20)},
                    allowed_company_ids=[a])
            else:
                result, error = FinancialBorderoService.update_settlement(bordero_id=bordero,
                    settlement_id=parent, company_id=a, payload={'gross_amount': 100}, allowed_company_ids=[a])
            if operation in ('satellite_failure', 'real_policy_failure'):
                assert result is None and error, 'Satellite failure was silently committed'
            else:
                assert result is not None and error is None, error
    finally:
        event.remove(engine, 'commit', committed)
    if operation in ('satellite_failure', 'real_policy_failure'):
        assert commits == []
        with app.app_context():
            saved = db.session.get(FinancialBordero, bordero)
            assert saved.settled_amount == 0 and saved.open_amount == Decimal('200')
            assert FinancialBorderoSettlement.query.filter_by(bordero_id=bordero).count() == 0
            assert FinancialSettlement.query.filter(FinancialSettlement.metadata_json.contains({'bordero_id': bordero})).count() == 0
            if operation == 'real_policy_failure':
                from models.financial import FinancialSatelliteExecution
                assert FinancialSatelliteExecution.query.filter_by(company_id=a, policy_id=policy_id).count() == 0
                assert 'bloqueado pelo borderô' in caplog.text
        return
    assert len(commits) == 1, commits
    with app.app_context():
        saved = db.session.get(FinancialBordero, bordero)
        assert saved.settled_amount == Decimal('100') and saved.open_amount == Decimal('100')
        items = saved.items.all()
        assert sum(item.settled_amount for item in items) == Decimal('100')
        assert sum(item.open_amount for item in items) == Decimal('100')
        parents = FinancialBorderoSettlement.query.filter_by(bordero_id=bordero, company_id=a, deleted_at=None).all()
        assert len(parents) == 1 and parents[0].gross_amount == Decimal('100')
        active = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == a, FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.metadata_json.contains({'bordero_id': bordero})).all()
        assert active and sum(row.principal_amount for row in active) == Decimal('100')
        if operation == 'edit':
            assert db.session.get(FinancialBorderoSettlement, parent).deleted_at is not None
            assert all(db.session.get(FinancialSettlement, key).deleted_at is not None for key in children)


def test_bordero_edit_failure_preserves_original_settlement(lab):
    app, (a, _, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'EDIT-FAIL')
    with app.app_context():
        db.session.get(FinancialSettlement, children[1]).reconciliation_status = 'pending'
        db.session.commit()
        engine = db.engine
    # Database fault injection, confined to the synthetic parent's replacement.
    with engine.begin() as conn:
        conn.execute(db.text(f'''CREATE FUNCTION lab_reject_replacement() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.bordero_id = {int(bordero)} THEN RAISE EXCEPTION 'SYNTHETIC replacement rejected'; END IF;
            RETURN NEW; END $$'''))
        conn.execute(db.text('CREATE TRIGGER lab_reject_replacement BEFORE INSERT ON financial_bordero_settlements FOR EACH ROW EXECUTE FUNCTION lab_reject_replacement()'))
    try:
        with app.app_context():
            result, error = FinancialBorderoService.update_settlement(bordero_id=bordero,
                settlement_id=parent, company_id=a, payload={'gross_amount': 100}, allowed_company_ids=[a])
            assert result is None and 'SYNTHETIC replacement rejected' in error, (result, error)
            db.session.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(db.text('DROP TRIGGER lab_reject_replacement ON financial_bordero_settlements'))
            conn.execute(db.text('DROP FUNCTION lab_reject_replacement()'))
    with app.app_context():
        assert db.session.get(FinancialBorderoSettlement, parent).deleted_at is None, 'Original parent lost after failed replacement'
        assert all(db.session.get(FinancialSettlement, key).deleted_at is None for key in children)
        saved = db.session.get(FinancialBordero, bordero)
        assert saved.settled_amount == Decimal('120') and saved.open_amount == Decimal('80')


def test_bordero_creation_failure_on_second_child_rolls_back_everything(lab):
    app, (a, _, _) = lab
    bordero, parent, children = seed_bordero_reversal(app, a, 'CREATE-FAIL')
    with app.app_context():
        schedule_second = db.session.get(FinancialEntry, db.session.get(FinancialSettlement, children[1]).financial_entry_id).financial_schedule_id
        for key in children:
            db.session.delete(db.session.get(FinancialSettlement, key))
        db.session.delete(db.session.get(FinancialBorderoSettlement, parent))
        saved = db.session.get(FinancialBordero, bordero)
        saved.settled_amount, saved.open_amount, saved.status = 0, 200, 'open'
        for item in saved.items.all():
            item.settled_amount, item.open_amount = 0, 100
        db.session.commit()
        engine = db.engine
    with engine.begin() as conn:
        conn.execute(db.text(f'''CREATE FUNCTION lab_reject_second_child() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF (SELECT financial_schedule_id FROM financial_entries WHERE id=NEW.financial_entry_id) = {int(schedule_second)}
            THEN RAISE EXCEPTION 'SYNTHETIC second child rejected'; END IF; RETURN NEW; END $$'''))
        conn.execute(db.text('CREATE TRIGGER lab_reject_second_child BEFORE INSERT ON financial_settlements FOR EACH ROW EXECUTE FUNCTION lab_reject_second_child()'))
    try:
        with app.app_context():
            result, error = FinancialBorderoService.create_settlement(bordero_id=bordero,
                payload={'company_id': a, 'gross_amount': 120, 'settlement_date': date(2026, 9, 20)}, allowed_company_ids=[a])
            assert result is None and 'SYNTHETIC second child rejected' in error, (result, error)
            db.session.rollback()
    finally:
        with engine.begin() as conn:
            conn.execute(db.text('DROP TRIGGER lab_reject_second_child ON financial_settlements'))
            conn.execute(db.text('DROP FUNCTION lab_reject_second_child()'))
    with app.app_context():
        assert FinancialBorderoSettlement.query.filter_by(bordero_id=bordero).count() == 0, 'Partial parent committed'
        assert FinancialSettlement.query.filter(FinancialSettlement.metadata_json.contains({'bordero_id': bordero})).count() == 0, 'Partial child committed'
        saved = db.session.get(FinancialBordero, bordero)
        assert saved.settled_amount == 0 and saved.open_amount == Decimal('200')
