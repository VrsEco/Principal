from datetime import date, timedelta

from models import db, Employee, EmployeeQualificationEvidence
from services.employee_role_occupancy_service import _actor, _date


def normalize(payload):
    allowed = {'qualification_name', 'level', 'evidence_source', 'evidence_reference', 'expires_on'}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError('Payload de qualificação inválido.')
    name = payload.get('qualification_name')
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 255:
        raise ValueError('Nome da qualificação é obrigatório e deve ter até 255 caracteres.')
    source = payload.get('evidence_source', 'declared')
    if source not in {'declared', 'documented', 'verified'}:
        raise ValueError('Origem da evidência inválida.')
    values = {'qualification_name': name.strip(), 'evidence_source': source, 'expires_on': _date(payload.get('expires_on'))}
    for field, limit in [('level', 80), ('evidence_reference', 500)]:
        value = payload.get(field)
        if value is not None and (not isinstance(value, str) or len(value.strip()) > limit):
            raise ValueError(f'{field} inválido.')
        values[field] = value.strip() or None if isinstance(value, str) else None
    return values


def create(company_id, employee_id, payload, *, actor_user_id):
    actor = _actor(actor_user_id)
    values = normalize(payload)
    Employee.query.filter_by(id=employee_id, company_id=company_id).with_for_update().first_or_404()
    existing = EmployeeQualificationEvidence.query.filter_by(company_id=company_id, employee_id=employee_id,
        qualification_name=values['qualification_name'], level=values['level']).first()
    if existing:
        raise ValueError('Qualificação já registrada para este colaborador neste nível.')
    record = EmployeeQualificationEvidence(company_id=company_id, employee_id=employee_id, created_by_user_id=actor, **values)
    db.session.add(record)
    db.session.flush()
    return record


def list_for_employee(company_id, employee_id, *, reference_date=None):
    """Lista evidências do tenant sem inferir aderência ao cargo."""
    Employee.query.filter_by(id=employee_id, company_id=company_id).first_or_404()
    today = _date(reference_date) if reference_date else date.today()
    warning_limit = today + timedelta(days=30)
    records = (EmployeeQualificationEvidence.query
               .filter_by(company_id=company_id, employee_id=employee_id)
               .order_by(EmployeeQualificationEvidence.expires_on.asc().nullslast(),
                         EmployeeQualificationEvidence.qualification_name.asc(),
                         EmployeeQualificationEvidence.id.asc())
               .all())
    items = []
    for record in records:
        item = record.to_dict()
        item['validity_status'] = ('no_expiry' if record.expires_on is None else
                                   'expired' if record.expires_on < today else
                                   'expires_soon' if record.expires_on <= warning_limit else 'valid')
        items.append(item)
    return {'company_id': company_id, 'employee_id': employee_id, 'as_of': today.isoformat(),
            'items': items, 'qualification_match_evaluated': False}
