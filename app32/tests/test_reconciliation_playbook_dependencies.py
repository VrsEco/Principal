"""Regression checks without Flask startup or database access."""
import pytest
from pydantic import ValidationError
from schemas.financial import FinancialReconciliationPlaybookInput as Input
from services.financial_reconciliation_playbook_service import FinancialReconciliationPlaybookService as Service
from services.financial_service import FinancialService


def payload():
    return dict(company_id=1, playbook_code='TEST', name='Teste', field_name='description', match_value='abc', action_type='classify_only')


def test_import_and_default_confirmation():
    assert Input(**payload()).confirmation_policy == 'always'


@pytest.mark.parametrize('changes', [dict(extra_field=True),dict(action_type='execute_anything'),dict(priority=-1)])
def test_invalid_payload_rejected(changes):
    with pytest.raises(ValidationError):
        Input(**(payload() | changes))


def test_scope_denial_precedes_database(monkeypatch):
    monkeypatch.setattr(FinancialService, '_ensure_company_scope', staticmethod(lambda *args: 'denied'))
    assert Service.create_playbook(payload=payload(), allowed_company_ids=[2]) == (None, 'denied')
    assert Service.list_playbooks(company_id=1, allowed_company_ids=[2]) == (None, 'denied')
    assert Service.update_playbook(company_id=1, playbook_id=1, payload={}, allowed_company_ids=[2]) == (None, 'denied')
    assert Service.suggest_for_row(company_id=1, import_row_id=1, allowed_company_ids=[2]) == (None, 'denied')


def test_model_matches_published_unique_and_indexes():
    from models.financial import FinancialReconciliationPlaybook
    table = FinancialReconciliationPlaybook.__table__
    assert {i.name for i in table.indexes} == {
        'ix_financial_reconciliation_playbooks_company_active',
        'ix_financial_reconciliation_playbooks_company_priority',
    }
    assert any(c.name == 'uq_financial_reconciliation_playbooks_company_code'
               and list(c.columns.keys()) == ['company_id', 'playbook_code']
               for c in table.constraints)
