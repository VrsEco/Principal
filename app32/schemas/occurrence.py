
from . import ma
from models import db
from models.occurrence import Occurrence
from marshmallow import fields, pre_dump
from models.employee import Employee

class OccurrenceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Occurrence
        include_fk = True
        load_instance = True
        sqla_session = db.session

    employee_name = fields.Function(lambda obj: obj.employee.name if obj.employee else None)
    process_name = fields.Function(lambda obj: obj.process.name if obj.process else None)
    project_name = fields.Function(lambda obj: obj.project.name if obj.project else None)
    company_name = fields.Function(lambda obj: obj.company.name if obj.company else None)
    
    # Override DateTime fields to handle potential string data from DB
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    collaborators_ids = fields.List(fields.Raw(), allow_none=True)
    collaborators_info = fields.Method("get_collaborators_info")

    def get_collaborators_info(self, obj):
        if not obj.collaborators_ids:
            return []
        if isinstance(obj.collaborators_ids, list):
            ids = [id for id in obj.collaborators_ids if isinstance(id, int)]
            if not ids: return []
            
            emps = Employee.query.filter(Employee.id.in_(ids)).with_entities(Employee.id, Employee.name).all()
            return [{"id": e.id, "name": e.name} for e in emps]
        return []

occurrence_schema = OccurrenceSchema()
occurrences_schema = OccurrenceSchema(many=True)
