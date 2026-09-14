
from datetime import datetime
from flask import request
from sqlalchemy import or_
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, Occurrence, Company, Employee
from schemas.occurrence import occurrence_schema, occurrences_schema
from utils.permissions import (
    active_company_permission_required,
    get_active_company_id,
    get_default_company_id,
    has_company_full_access,
)
from flask import session
from flask_login import current_user

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."

def get_request_company_id():
    def clean(val):
        if val is None: return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''): return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # The active session owns the tenant boundary.  Client supplied IDs are
    # only validated by the active-company decorator; they never select data.
    cid = clean(session.get('active_company_id'))
    if cid is not None: return cid

    if current_user.is_authenticated:
        default_company_id = get_default_company_id()
        if default_company_id:
            session['active_company_id'] = default_company_id
            return default_company_id
    return None



def _get_current_employee(company_id):
    if not current_user.is_authenticated or not company_id:
        return None
    return Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()


def _occurrence_visible_to_employee(occurrence, employee_id):
    if not occurrence or not employee_id:
        return False
    if occurrence.employee_id == employee_id:
        return True

    collaborators = occurrence.collaborators_ids or []
    if isinstance(collaborators, list):
        for item in collaborators:
            if item == employee_id:
                return True
            if isinstance(item, dict):
                raw_id = item.get('employee_id') or item.get('id')
                try:
                    if raw_id is not None and int(raw_id) == int(employee_id):
                        return True
                except (TypeError, ValueError):
                    continue
    return False


def _get_occurrence_with_access(occurrence_id, action='view'):
    occurrence = Occurrence.query.get_or_404(occurrence_id)
    company_id = occurrence.company_id
    if company_id != get_active_company_id():
        return None

    if not has_company_full_access(company_id):
        employee = _get_current_employee(company_id)
        if not employee or not _occurrence_visible_to_employee(occurrence, employee.id):
            return None

    return occurrence

class OccurrenceListResource(Resource):
    @active_company_permission_required('processes', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200
            
        process_id = request.args.get('process_id', type=int)
        project_id = request.args.get('project_id', type=int)
        employee_id = request.args.get('employee_id', type=int)
        type_filter = (request.args.get('type') or '').strip()
        search = (request.args.get('search') or '').strip()
        date_start = request.args.get('date_start', type=str)
        date_end = request.args.get('date_end', type=str)
        paginated = (request.args.get('paginated') or 'false').lower() == 'true'

        query = Occurrence.query.filter_by(company_id=company_id)
        employee = None

        if not has_company_full_access(company_id):
            employee = _get_current_employee(company_id)
            if not employee:
                return [], 200

        if process_id:
            query = query.filter_by(process_id=process_id)
        if project_id:
            query = query.filter_by(project_id=project_id)
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        if type_filter == 'positive':
            query = query.filter(or_(Occurrence.score > 0, Occurrence.type.in_(['positive', 'compliment', 'improvement', 'idea'])))
        elif type_filter == 'negative':
            query = query.filter(or_(Occurrence.score < 0, Occurrence.type.in_(['negative', 'incident', 'complaint'])))
        elif type_filter:
            query = query.filter_by(type=type_filter)
        if search:
            pattern = f'%{search}%'
            query = query.filter(or_(Occurrence.title.ilike(pattern), Occurrence.description.ilike(pattern)))
        for raw_date, comparator in ((date_start, 'start'), (date_end, 'end')):
            if not raw_date:
                continue
            try:
                parsed = datetime.fromisoformat(raw_date)
            except ValueError:
                continue
            query = query.filter(Occurrence.created_at >= parsed if comparator == 'start' else Occurrence.created_at < parsed.replace(hour=23, minute=59, second=59, microsecond=999999))

        occurrences = query.order_by(Occurrence.created_at.desc()).all()

        if employee_id:
            occurrences = [occ for occ in occurrences if _occurrence_visible_to_employee(occ, employee_id)]
        if employee and not has_company_full_access(company_id):
            occurrences = [occ for occ in occurrences if _occurrence_visible_to_employee(occ, employee.id)]

        if paginated:
            page = max(request.args.get('page', 1, type=int) or 1, 1)
            per_page = min(max(request.args.get('per_page', 50, type=int) or 50, 1), 100)
            total = len(occurrences)
            items = occurrences[(page - 1) * per_page: page * per_page]
            return {'items': occurrences_schema.dump(items), 'pagination': {'page': page, 'per_page': per_page, 'total': total, 'has_more': page * per_page < total}}, 200
        return occurrences_schema.dump(occurrences), 200

    @active_company_permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json() or {}
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            # Allow created_at to be auto-set if not provided, or parse it if provided
            # Schema handles string to DateTime if format is correct
                
            if not has_company_full_access(data.get('company_id')):
                employee = _get_current_employee(data.get('company_id'))
                if not employee:
                    return {"error": "Colaborador sem vínculo ativo na empresa."}, 403
                data['employee_id'] = employee.id
                data['collaborators_ids'] = [employee.id]

            occurrence = occurrence_schema.load(data)
            db.session.add(occurrence)
            db.session.commit()
            return occurrence_schema.dump(occurrence), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class OccurrenceResource(Resource):
    @active_company_permission_required('processes', 'view')
    def get(self, occurrence_id):
        occurrence = _get_occurrence_with_access(occurrence_id, action='view')
        if not occurrence:
            return {"error": "Acesso negado à ocorrência."}, 403
        return occurrence_schema.dump(occurrence), 200

    @active_company_permission_required('processes', 'edit')
    def put(self, occurrence_id):
        occurrence = _get_occurrence_with_access(occurrence_id, action='edit')
        if not occurrence:
            return {"error": "Acesso negado à ocorrência."}, 403
        try:
            data = request.get_json() or {}
            if not has_company_full_access(occurrence.company_id):
                employee = _get_current_employee(occurrence.company_id)
                if not employee:
                    return {"error": "Colaborador sem vínculo ativo na empresa."}, 403
                data['employee_id'] = employee.id
                data['collaborators_ids'] = [employee.id]
            occurrence = occurrence_schema.load(data, instance=occurrence, partial=True)
            db.session.commit()
            return occurrence_schema.dump(occurrence), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @active_company_permission_required('processes', 'delete')
    def delete(self, occurrence_id):
        occurrence = _get_occurrence_with_access(occurrence_id, action='delete')
        if not occurrence:
            return {"error": "Acesso negado à ocorrência."}, 403
        try:
            db.session.delete(occurrence)
            db.session.commit()
            return {"message": "Occurrence deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500
