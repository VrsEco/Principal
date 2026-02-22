from marshmallow import fields, post_load
from schemas import ma
from models import Project, ProjectTask

class ProjectTaskSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProjectTask
        load_instance = True
        include_fk = True
    
    code = fields.String(dump_only=True)
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    score_weight = fields.Float()
    estimated_hours = fields.Float()
    worked_hours = fields.Float()
    employee_name = fields.String(dump_only=True)
    project_name = fields.String(dump_only=True)

class ProjectSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Project
        load_instance = True
        include_fk = True
    
    code = fields.String(dump_only=True)
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    task_stats = fields.Dict(dump_only=True)
    portfolio_id = fields.Integer(allow_none=True)  # Explicitly include portfolio_id
    
    tasks = fields.Nested(ProjectTaskSchema, many=True, dump_only=True)

project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)
project_task_schema = ProjectTaskSchema()
project_tasks_schema = ProjectTaskSchema(many=True)
