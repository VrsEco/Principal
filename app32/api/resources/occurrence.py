
from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, Occurrence, Company, Employee
from schemas.occurrence import occurrence_schema, occurrences_schema
from utils.permissions import permission_required
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
        if current_user.role == 'admin':
            first = Company.query.order_by(Company.id).first()
            if first:
                session['active_company_id'] = first.id
                return first.id
        else:
            emp = Employee.query.filter_by(user_id=current_user.id, status='active').order_by(Employee.company_id).first()
            if emp:
                session['active_company_id'] = emp.company_id
                return emp.company_id
    return None

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
        
        if process_id:
            query = query.filter_by(process_id=process_id)
        if project_id:
            query = query.filter_by(project_id=project_id)
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        if type_filter:
            query = query.filter_by(type=type_filter)
            
        occurrences = query.order_by(Occurrence.created_at.desc()).all()
        return occurrences_schema.dump(occurrences), 200

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            # Allow created_at to be auto-set if not provided, or parse it if provided
            # Schema handles string to DateTime if format is correct
                
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
        occurrence = Occurrence.query.get_or_404(occurrence_id)
        return occurrence_schema.dump(occurrence), 200

    @permission_required('processes', 'edit')
    def put(self, occurrence_id):
        occurrence = Occurrence.query.get_or_404(occurrence_id)
        try:
            data = request.get_json()
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
        occurrence = Occurrence.query.get_or_404(occurrence_id)
        try:
            db.session.delete(occurrence)
            db.session.commit()
            return {"message": "Occurrence deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500
