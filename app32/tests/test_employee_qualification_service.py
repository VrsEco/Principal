from datetime import date, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from models import EmployeeQualificationEvidence
from services.employee_qualification_service import list_for_employee, normalize


def test_normalizes_evidence_without_declaring_qualification_match():
    item = normalize({'qualification_name': ' Excel avançado ', 'level': ' Intermediário ', 'evidence_source': 'documented', 'expires_on': '2027-01-01'})
    assert item['qualification_name'] == 'Excel avançado'
    assert item['level'] == 'Intermediário'
    assert 'meets_requirement' not in item


@pytest.mark.parametrize('payload', [{}, {'qualification_name': ''}, {'qualification_name': 'x', 'evidence_source': 'auto'}, {'qualification_name': 'x', 'expires_on': '2027/01/01'}, {'qualification_name': 'x', 'unexpected': 1}])
def test_invalid_contract(payload):
    with pytest.raises(ValueError): normalize(payload)


def test_postgres_tenant_fk_and_source_constraint():
    ddl = str(CreateTable(EmployeeQualificationEvidence.__table__).compile(dialect=postgresql.dialect()))
    assert 'FOREIGN KEY(company_id, employee_id)' in ddl
    assert "evidence_source IN ('declared', 'documented', 'verified')" in ddl


def test_list_status_is_validity_only_and_never_a_role_match(monkeypatch):
    from services import employee_qualification_service as service
    employee_query = Mock(); employee_query.filter_by.return_value.first_or_404.return_value = Mock()
    monkeypatch.setattr(service, 'Employee', Mock(query=employee_query))
    expired = Mock(expires_on=date.today() - timedelta(days=1)); expired.to_dict.return_value = {'id': 1}
    soon = Mock(expires_on=date.today() + timedelta(days=5)); soon.to_dict.return_value = {'id': 2}
    no_expiry = Mock(expires_on=None); no_expiry.to_dict.return_value = {'id': 3}
    records = Mock(); records.filter_by.return_value.order_by.return_value.all.return_value = [expired, soon, no_expiry]
    monkeypatch.setattr(service, 'EmployeeQualificationEvidence', Mock(query=records))
    snapshot = list_for_employee(7, 12, reference_date=date.today().isoformat())
    assert [item['validity_status'] for item in snapshot['items']] == ['expired', 'expires_soon', 'no_expiry']
    assert snapshot['qualification_match_evaluated'] is False
