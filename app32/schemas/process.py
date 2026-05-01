from marshmallow import fields
from . import ma
from marshmallow import fields, EXCLUDE
from models.process import ProcessArea, MacroProcess, Process, ProcessBpmnDiagram, ProcessRoutine, ProcessStep, ProcessInstance, ProcessInstanceExecution, ProcessActivityExecutionContract

class ProcessStepSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessStep
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)

class ProcessRoutineSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessRoutine
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    # POP routines usam order_index para ordenação
    code = fields.String()
    order_index = fields.Integer()

    # Evitar carregar steps via relationship (process_steps pode referenciar tabelas diferentes)
    steps = fields.List(fields.Dict(), dump_only=True)

class ProcessBpmnDiagramSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessBpmnDiagram
        load_instance = True
        include_fk = True
        unknown = EXCLUDE

    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    published_at = fields.String(dump_only=True)
    metadata_json = fields.Dict(allow_none=True)

class ProcessSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Process
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    # ⚠️ Importante: não serializar rotinas aqui por padrão.
    # Em bancos herdados (app31/app32), a tabela `routines` pode não ter colunas esperadas por versões antigas do ORM.
    # Rotinas e passos são carregados por endpoints específicos em `api/routes/processes.py`.
    # CHANGED: Removed exclude=("processes",) because MacroProcessSchema does not have processes field by default
    macro = fields.Nested("MacroProcessSchema", dump_only=True)

class MacroProcessSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = MacroProcess
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    # Evitar aninhamento recursivo pesado (área -> macros -> processos -> rotinas)
    # CHANGED: Removed exclude=("macros",) because ProcessAreaSchema does not have macros field by default
    area = fields.Nested("ProcessAreaSchema", dump_only=True)

class ProcessAreaSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessArea
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    # Evitar aninhamento recursivo pesado; para mapa/kanban as telas consomem endpoints separados

class ProcessInstanceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessInstance
        load_instance = True
        include_fk = True
        unknown = EXCLUDE
    
    worked_hours = fields.Float()
    estimated_hours = fields.Float()
    actual_hours = fields.Float()
    
    started_at = fields.DateTime(format='iso', allow_none=True)
    completed_at = fields.DateTime(format='iso', allow_none=True)
    paused_at = fields.DateTime(format='iso', allow_none=True)
    process_bpmn_diagram_id = fields.Integer(allow_none=True)
    process_version = fields.Integer(allow_none=True)
    current_bpmn_element_id = fields.String(allow_none=True)
    pause_reason = fields.String(allow_none=True)
    runtime_context_json = fields.Dict(allow_none=True)
    trigger_type = fields.String()
    score_weight = fields.Float()
    actual_end_date = fields.Method("get_actual_end_date", "load_actual_end_date", allow_none=True)
    # Allow frontend to send 'end_date' which maps to actual_end_date logic
    end_date = fields.Method("get_actual_end_date", "load_actual_end_date", allow_none=True)
    
    due_date = fields.Method("get_due_date", "load_due_date", allow_none=True)
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    normalized_collaborators = fields.Method("get_normalized_collaborators", dump_only=True)
    process_name = fields.Method("get_process_name", dump_only=True)
    process_code = fields.Method("get_process_code", dump_only=True)

    def get_due_date(self, obj):
        if not obj.due_date: return None
        if hasattr(obj.due_date, 'isoformat'):
            return obj.due_date.isoformat()
        return str(obj.due_date)

    def load_due_date(self, value):
        if not value: return None
        if isinstance(value, str):
            try:
                from datetime import datetime
                return datetime.strptime(value.split('T')[0], '%Y-%m-%d').date()
            except:
                return value
        return value

    def get_actual_end_date(self, obj):
        if not obj.actual_end_date: return None
        if hasattr(obj.actual_end_date, 'isoformat'):
            return obj.actual_end_date.isoformat()
        return str(obj.actual_end_date)

    def load_actual_end_date(self, value):
        if not value: return None
        if isinstance(value, str):
            try:
                from datetime import datetime
                # Handle YYYY-MM-DD format
                return datetime.strptime(value.split('T')[0], '%Y-%m-%d').date()
            except:
                return value
        return value

    def get_normalized_collaborators(self, obj):
        # This is overridden in the resource/view to include names
        return []

    def get_process_name(self, obj):
        return obj.process_rel.name if obj.process_rel else None

    def get_process_code(self, obj):
        return obj.process_rel.code if obj.process_rel else None

class ProcessInstanceExecutionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessInstanceExecution
        load_instance = True
        include_fk = True
        unknown = EXCLUDE

    estimated_hours = fields.Float()
    actual_hours = fields.Float()
    started_at = fields.DateTime(format='iso', allow_none=True)
    completed_at = fields.DateTime(format='iso', allow_none=True)
    paused_at = fields.DateTime(format='iso', allow_none=True)
    waiting_since = fields.DateTime(format='iso', allow_none=True)
    request_payload_json = fields.Dict(allow_none=True)
    response_payload_json = fields.Dict(allow_none=True)
    error_payload_json = fields.Dict(allow_none=True)
    metadata_json = fields.Dict(allow_none=True)
    created_at = fields.DateTime(format='iso', dump_only=True)
    updated_at = fields.DateTime(format='iso', dump_only=True)

class ProcessActivityExecutionContractSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProcessActivityExecutionContract
        load_instance = True
        include_fk = True
        unknown = EXCLUDE

    ui_schema_json = fields.Dict(allow_none=True)
    rest_config_json = fields.Dict(allow_none=True)
    mcp_config_json = fields.Dict(allow_none=True)
    completion_rules_json = fields.Dict(allow_none=True)
    created_at = fields.DateTime(format='iso', dump_only=True)
    updated_at = fields.DateTime(format='iso', dump_only=True)

# Instances for easy import
process_schema = ProcessSchema()
processes_schema = ProcessSchema(many=True)
macro_process_schema = MacroProcessSchema()
macro_processes_schema = MacroProcessSchema(many=True)
process_area_schema = ProcessAreaSchema()
process_areas_schema = ProcessAreaSchema(many=True)
process_routine_schema = ProcessRoutineSchema()
process_routines_schema = ProcessRoutineSchema(many=True)
process_bpmn_diagram_schema = ProcessBpmnDiagramSchema()
process_bpmn_diagrams_schema = ProcessBpmnDiagramSchema(many=True)
process_step_schema = ProcessStepSchema()
process_steps_schema = ProcessStepSchema(many=True)
process_instance_schema = ProcessInstanceSchema()
process_instances_schema = ProcessInstanceSchema(many=True)
process_instance_execution_schema = ProcessInstanceExecutionSchema()
process_instance_executions_schema = ProcessInstanceExecutionSchema(many=True)
process_activity_execution_contract_schema = ProcessActivityExecutionContractSchema()
process_activity_execution_contracts_schema = ProcessActivityExecutionContractSchema(many=True)
