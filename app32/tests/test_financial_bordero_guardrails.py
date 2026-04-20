import os
import sys
from decimal import Decimal
from types import SimpleNamespace

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


class _SessionStub:
    def add(self, *_args, **_kwargs):
        return None

    def flush(self):
        return None

    def commit(self):
        return None

    def rollback(self):
        return None


class _ColumnStub:
    def __eq__(self, _other):
        return True

    def is_(self, _other):
        return True


def test_ensure_schedule_is_available_blocks_titles_locked_in_other_bordero(monkeypatch):
    monkeypatch.setattr(
        FinancialBorderoService,
        'get_active_bordero_for_schedule',
        staticmethod(lambda **kwargs: SimpleNamespace(id=9, bordero_code='B-9')),
    )

    error = FinancialBorderoService._ensure_schedule_is_available(company_id=7, schedule_id=15, exclude_bordero_id=3)

    assert error == 'Título Financeiro já participa do borderô B-9.'


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
