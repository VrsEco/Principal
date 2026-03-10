
from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, Occurrence, Company, Employee
from schemas.occurrence import occurrence_schema, occurrences_schema
from utils.permissions import get_default_company_id, has_company_full_access, permission_required
from flask import session
from flask_login import current_user

def get_request_company_id():
    def clean(val):
        if val is None: return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''): return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    cid = clean(request.args.get('company_id'))
    if cid is not None: return cid
    
    try:
        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None: return cid
    except:
        pass

    cid = clean(session.get('active_company_id'))
    if cid:
        return cid

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

    if not has_company_full_access(company_id):
        employee = _get_current_employee(company_id)
        if not employee or not _occurrence_visible_to_employee(occurrence, employee.id):
            return None

    return occurrence

class OccurrenceListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200
            
        process_id = request.args.get('process_id')
        project_id = request.args.get('project_id')
        employee_id = request.args.get('employee_id')
        type_filter = request.args.get('type')

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
        if type_filter:
            query = query.filter_by(type=type_filter)

        occurrences = query.order_by(Occurrence.created_at.desc()).all()

        if employee and not has_company_full_access(company_id):
            occurrences = [occ for occ in occurrences if _occurrence_visible_to_employee(occ, employee.id)]

        return occurrences_schema.dump(occurrences), 200

    @permission_required('processes', 'create')
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
            return {"error": str(e)}, 500

class OccurrenceResource(Resource):
    @permission_required('processes', 'view')
    def get(self, occurrence_id):
        occurrence = _get_occurrence_with_access(occurrence_id, action='view')
        if not occurrence:
            return {"error": "Acesso negado à ocorrência."}, 403
        return occurrence_schema.dump(occurrence), 200

    @permission_required('processes', 'edit')
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
            return {"error": str(e)}, 500

    @permission_required('processes', 'delete')
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
            return {"error": str(e)}, 500
