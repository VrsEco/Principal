import os
import sys
from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_bordero_service as bordero_module
from services.financial_bordero_service import FinancialBorderoService


class _QueryStub:
    def __init__(self, first_result):
        self._first_result = first_result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result


class _AllQueryStub:
    def __init__(self, all_result):
        self._all_result = all_result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self._all_result


class _SessionStub:
    def add(self, *_args, **_kwargs):
        return None

    def flush(self):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None


class _RetryBorderoSessionStub:
    def __init__(self):
        self.added = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def add(self, obj):
        self.added.append(obj)
        return None

    def flush(self):
        self.flush_calls += 1
        if self.flush_calls == 1:
            raise IntegrityError(
                "INSERT INTO financial_borderos ...",
                {},
                SimpleNamespace(diag=SimpleNamespace(constraint_name='uq_financial_borderos_company_code')),
            )
        for obj in reversed(self.added):
            if hasattr(obj, 'bordero_code'):
                obj.id = obj.id or 99
                break
        return None

    def commit(self):
        self.commit_calls += 1
        return None

    def rollback(self):
        self.rollback_calls += 1
        self.added.clear()
        return None


class _ColumnStub:
    def __eq__(self, _other):
        return True

    def is_(self, _other):
        return True

    def asc(self):
        return self

    def desc(self):
        return self


def test_ensure_schedule_is_available_blocks_titles_locked_in_other_bordero(monkeypatch):
    monkeypatch.setattr(
        FinancialBorderoService,
        'get_active_bordero_for_schedule',
        staticmethod(lambda **kwargs: SimpleNamespace(id=9, bordero_code='B-9')),
    )

    error = FinancialBorderoService._ensure_schedule_is_available(company_id=7, schedule_id=15, exclude_bordero_id=3)

    assert error == 'Título Financeiro já participa do borderô B-9.'


def test_generate_bordero_code_does_not_reuse_soft_deleted_code(monkeypatch):
    borderos = [
        SimpleNamespace(id=3, bordero_code='B-3', deleted_at=None),
        SimpleNamespace(id=2, bordero_code='B-2', deleted_at='2026-05-31'),
        SimpleNamespace(id=1, bordero_code='B-1', deleted_at='2026-05-30'),
    ]
    fake_model = type(
        'FinancialBorderoStub',
        (),
        {'company_id': _ColumnStub(), 'id': _ColumnStub(), 'query': _AllQueryStub(borderos)},
    )
    monkeypatch.setattr(bordero_module, 'FinancialBordero', fake_model)

    assert FinancialBorderoService._generate_bordero_code(7) == 'B-4'


def test_generate_bordero_settlement_code_does_not_reuse_soft_deleted_code(monkeypatch):
    settlements = [
        SimpleNamespace(id=12, settlement_code='B-31-BX-002', deleted_at=None),
        SimpleNamespace(id=11, settlement_code='B-31-BX-001', deleted_at='2026-05-31'),
        SimpleNamespace(id=10, settlement_code='B-30-BX-099', deleted_at=None),
    ]
    fake_model = type(
        'FinancialBorderoSettlementStub',
        (),
        {'company_id': _ColumnStub(), 'id': _ColumnStub(), 'query': _AllQueryStub(settlements)},
    )
    monkeypatch.setattr(bordero_module, 'FinancialBorderoSettlement', fake_model)

    assert FinancialBorderoService._generate_bordero_settlement_code(7, 'B-31') == 'B-31-BX-003'


def test_create_bordero_rejects_non_operational_title(monkeypatch):
    fake_schedule = SimpleNamespace(id=15, company_id=7, entry_type='payable', deleted_at=None)
    fake_model = type('FinancialScheduleStub', (), {'id': _ColumnStub(), 'company_id': _ColumnStub(), 'deleted_at': _ColumnStub(), 'query': _QueryStub(fake_schedule)})
    monkeypatch.setattr(bordero_module, 'FinancialSchedule', fake_model)
    monkeypatch.setattr(bordero_module.db, 'session', _SessionStub())
    monkeypatch.setattr(bordero_module, 'FinancialBordero', lambda **kwargs: SimpleNamespace(id=1, bordero_code='B-1'))
    monkeypatch.setattr(FinancialBorderoService, '_generate_bordero_code', staticmethod(lambda company_id: 'B-1'))
    monkeypatch.setattr(FinancialBorderoService, '_build_schedule_snapshot', staticmethod(lambda schedule: {'summary': {'operational_state': 'forecast', 'open_total': Decimal('100')}}))
    monkeypatch.setattr(FinancialBorderoService, '_ensure_schedule_is_available', staticmethod(lambda **kwargs: None))

    payload = {
        'company_id': 7,
        'bordero_type': 'payable',
        'name': 'Borderô teste',
        'items': [{'financial_schedule_id': 15, 'selected_amount': '100'}],
    }

    result, error = FinancialBorderoService.create_bordero(payload=payload, allowed_company_ids=[7])

    assert result is None
    assert error == 'Somente Títulos Financeiros operacionais com saldo aberto podem entrar em borderô.'


def test_create_bordero_retries_when_company_code_collides(monkeypatch):
    fake_schedule = SimpleNamespace(id=15, company_id=7, entry_type='payable', deleted_at=None, schedule_code='SCH-15')
    fake_schedule_model = type(
        'FinancialScheduleStub',
        (),
        {'id': _ColumnStub(), 'company_id': _ColumnStub(), 'deleted_at': _ColumnStub(), 'query': _QueryStub(fake_schedule)},
    )
    retry_session = _RetryBorderoSessionStub()
    generated_codes = iter(['B-1', 'B-2'])

    monkeypatch.setattr(bordero_module, 'FinancialSchedule', fake_schedule_model)
    monkeypatch.setattr(bordero_module.db, 'session', retry_session)
    monkeypatch.setattr(
        bordero_module,
        'FinancialBordero',
        lambda **kwargs: SimpleNamespace(id=None, total_amount=Decimal('0.00'), settled_amount=Decimal('0.00'), open_amount=Decimal('0.00'), **kwargs),
    )
    monkeypatch.setattr(bordero_module, 'FinancialBorderoItem', lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(FinancialBorderoService, '_generate_bordero_code', staticmethod(lambda company_id: next(generated_codes)))
    monkeypatch.setattr(
        FinancialBorderoService,
        '_build_schedule_snapshot',
        staticmethod(lambda schedule: {'summary': {'operational_state': 'active', 'open_total': Decimal('100.00')}}),
    )
    monkeypatch.setattr(FinancialBorderoService, '_ensure_schedule_is_available', staticmethod(lambda **kwargs: None))
    monkeypatch.setattr(
        FinancialBorderoService,
        '_serialize_bordero',
        staticmethod(lambda bordero, **kwargs: {'id': bordero.id, 'bordero_code': bordero.bordero_code}),
    )

    payload = {
        'company_id': 7,
        'bordero_type': 'payable',
        'name': 'Borderô retry',
        'items': [{'financial_schedule_id': 15, 'selected_amount': '100.00'}],
    }

    result, error = FinancialBorderoService.create_bordero(payload=payload, allowed_company_ids=[7])

    assert error is None
    assert result == {'id': 99, 'bordero_code': 'B-2'}
    assert retry_session.flush_calls == 2
    assert retry_session.rollback_calls == 1
    assert retry_session.commit_calls == 1


def test_bordero_settlement_audit_metadata_is_complete():
    bordero = SimpleNamespace(id=31, company_id=9, bordero_code='B-31')
    settlement = SimpleNamespace(id=55, settlement_code='B-31-BX-001')
    metadata = FinancialBorderoService._build_bordero_settlement_audit_metadata(
        base_metadata={'origin': 'qa'},
        bordero=bordero,
        settlement=settlement,
        gross_amount=Decimal('300.00'),
        allocated_total=Decimal('300.00'),
        variance_amount=Decimal('0.00'),
        allocation_payload=[
            {
                'bordero_item_id': 1,
                'financial_schedule_id': 101,
                'allocated_amount': 200.0,
                'entry_allocations': [{'financial_entry_id': 900, 'allocated_amount': 200.0}],
            },
            {
                'bordero_item_id': 2,
                'financial_schedule_id': 102,
                'allocated_amount': 100.0,
                'entry_allocations': [{'financial_entry_id': 901, 'allocated_amount': 100.0}],
            },
        ],
        created_by_user_id=7,
        created_by_employee_id=8,
        created_by_agent='app32',
    )

    assert metadata['traceability_contract'] == 'financial_bordero_settlement_v2'
    assert metadata['reconcile_via_bordero'] is True
    assert metadata['allocation_summary']['title_count'] == 2
    assert metadata['allocation_summary']['entry_settlement_count'] == 2
    assert metadata['audit']['tenant_scope']['company_id'] == 9
    assert metadata['audit']['actor']['user_id'] == 7


def test_sync_bordero_totals_from_items_marks_partial_and_settled():
    bordero = SimpleNamespace(total_amount=Decimal('0'), settled_amount=Decimal('0'), open_amount=Decimal('0'), status='open')
    items = [
        SimpleNamespace(selected_amount=Decimal('200.00'), settled_amount=Decimal('50.00'), open_amount=Decimal('150.00')),
        SimpleNamespace(selected_amount=Decimal('100.00'), settled_amount=Decimal('0.00'), open_amount=Decimal('100.00')),
    ]

    summary = FinancialBorderoService._sync_bordero_totals_from_items(bordero, items)

    assert summary['total_amount'] == Decimal('300.00')
    assert summary['settled_amount'] == Decimal('50.00')
    assert summary['open_amount'] == Decimal('250.00')
    assert summary['status'] == 'partially_settled'
    assert bordero.status == 'partially_settled'

    items[0].settled_amount = Decimal('200.00')
    items[0].open_amount = Decimal('0.00')
    items[1].settled_amount = Decimal('100.00')
    items[1].open_amount = Decimal('0.00')

    summary = FinancialBorderoService._sync_bordero_totals_from_items(bordero, items)

    assert summary['settled_amount'] == Decimal('300.00')
    assert summary['open_amount'] == Decimal('0.00')
    assert summary['status'] == 'settled'
    assert bordero.status == 'settled'


def test_recalculate_item_totals_from_settlements_reopens_bordero_items(monkeypatch):
    bordero = SimpleNamespace(id=7, company_id=3, total_amount=Decimal('300.00'), settled_amount=Decimal('300.00'), open_amount=Decimal('0.00'), status='settled')
    items = [
        SimpleNamespace(id=1, selected_amount=Decimal('200.00'), settled_amount=Decimal('200.00'), open_amount=Decimal('0.00')),
        SimpleNamespace(id=2, selected_amount=Decimal('100.00'), settled_amount=Decimal('100.00'), open_amount=Decimal('0.00')),
    ]
    active_settlements = [
        SimpleNamespace(metadata_json={'allocations': [{'bordero_item_id': 1, 'allocated_amount': 50.0}]})
    ]

    class _AllQuery:
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def all(self):
            return active_settlements

    fake_settlement_model = type(
        'FinancialBorderoSettlementStub',
        (),
        {'company_id': _ColumnStub(), 'bordero_id': _ColumnStub(), 'deleted_at': _ColumnStub(), 'settlement_date': _ColumnStub(), 'id': _ColumnStub(), 'query': _AllQuery()},
    )
    monkeypatch.setattr(bordero_module, 'FinancialBorderoSettlement', fake_settlement_model)

    result = FinancialBorderoService._recalculate_item_totals_from_settlements(bordero=bordero, items=items)

    assert result[1]['settled_amount'] == Decimal('50.00')
    assert result[1]['open_amount'] == Decimal('150.00')
    assert result[2]['settled_amount'] == Decimal('0.00')
    assert result[2]['open_amount'] == Decimal('100.00')
    assert bordero.status == 'partially_settled'


def test_validate_bordero_settlement_payload_respects_available_amount_override(monkeypatch):
    monkeypatch.setattr(
        bordero_module.FinancialCatalogService,
        'validate_reference_ids',
        staticmethod(lambda **kwargs: None),
    )
    bordero = SimpleNamespace(company_id=3, bank_account_id=None, open_amount=Decimal('20.00'))

    payload, error = FinancialBorderoService._validate_bordero_settlement_payload(
        bordero=bordero,
        payload={
            'company_id': 3,
            'settlement_date': '2026-05-15',
            'gross_amount': '50.00',
        },
        available_amount=Decimal('50.00'),
    )

    assert error is None
    assert payload['gross_amount'] == Decimal('50.00')
