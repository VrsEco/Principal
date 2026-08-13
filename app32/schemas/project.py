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
    is_deleted = fields.Boolean(dump_only=True)
    deleted_at = fields.String(dump_only=True)
    deleted_by_user_id = fields.Integer(dump_only=True)
    delete_reason = fields.String(dump_only=True)

class ProjectSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Project
        load_instance = True
        include_fk = True
    
    code = fields.String(dump_only=True)
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    task_stats = fields.Dict(dump_only=True)
    deadline = fields.Date(attribute="deadline", allow_none=True)
    portfolio_id = fields.Integer(allow_none=True)  # Explicitly include portfolio_id
    
    # Atividades são carregadas pelo endpoint paginado específico do projeto.


class ProjectListSchema(ma.SQLAlchemyAutoSchema):
    """Contrato leve para coleções; atividades possuem endpoint próprio."""

    class Meta:
        model = Project
        load_instance = False
        include_fk = True

    code = fields.String(dump_only=True)
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    deadline = fields.Date(attribute="deadline", allow_none=True)
    portfolio_id = fields.Integer(allow_none=True)

project_schema = ProjectSchema()
projects_schema = ProjectListSchema(many=True)
project_task_schema = ProjectTaskSchema()
project_tasks_schema = ProjectTaskSchema(many=True)
