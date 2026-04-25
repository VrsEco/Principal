from . import db
from datetime import datetime

class ProcessArea(db.Model):
    __tablename__ = 'process_areas'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, default=0)
    color = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    macros = db.relationship('MacroProcess', backref='area', lazy='dynamic', cascade='all, delete-orphan')

class MacroProcess(db.Model):
    __tablename__ = 'macro_processes'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('process_areas.id'), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    owner = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    processes = db.relationship('Process', backref='macro', lazy='dynamic', cascade='all, delete-orphan')

class Process(db.Model):
    __tablename__ = 'processes'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    macro_id = db.Column(db.Integer, db.ForeignKey('macro_processes.id'), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    responsible = db.Column(db.String(255), nullable=True)
    responsible_id = db.Column(db.Integer, nullable=True)
    owner_employee_id = db.Column(db.Integer, nullable=True)
    kanban_stage = db.Column(db.String(50), default='inbox') # inbox, designing, deploying, stabilizing, stable
    structuring_level = db.Column(db.String(50), nullable=True)
    performance_level = db.Column(db.String(50), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    flow_document = db.Column(db.String(255), nullable=True)
    flow_mermaid = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    routines = db.relationship('ProcessRoutine', backref='process', lazy='dynamic', cascade='all, delete-orphan')

class ProcessBpmnDiagram(db.Model):
    __tablename__ = 'process_bpmn_diagrams'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(30), nullable=False, default='draft')  # draft, published, archived
    name = db.Column(db.String(255), nullable=True)
    bpmn_xml = db.Column(db.Text, nullable=False)
    svg_snapshot = db.Column(db.Text, nullable=True)
    png_snapshot = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    process = db.relationship('Process', backref=db.backref('bpmn_diagrams', lazy='dynamic', cascade='all, delete-orphan'))

class ProcessRoutine(db.Model):
    __tablename__ = 'process_routines'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=False)
    code = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, default=0)
    bpmn_element_id = db.Column(db.String(255), nullable=True)
    bpmn_element_type = db.Column(db.String(80), nullable=True)
    bpmn_data_objects = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    steps = db.relationship(
        'ProcessStep',
        primaryjoin="ProcessRoutine.id==ProcessStep.routine_id",
        foreign_keys='ProcessStep.routine_id',
        lazy='dynamic',
        cascade='all, delete-orphan',
        backref='pop_routine'
    )

class ProcessStep(db.Model):
    __tablename__ = 'process_steps'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, nullable=False)  # Pode referenciar routines ou process_routines
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    expected_result = db.Column(db.Text, nullable=True)
    layout = db.Column(db.String(50), default='single') # single, dual
    image_path = db.Column(db.String(255), nullable=True)
    image_width = db.Column(db.Integer, default=280)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProcessInstance(db.Model):
    __tablename__ = 'process_instances'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey('processes.id'), nullable=False)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.id'), nullable=True)
    instance_code = db.Column(db.String(100))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending') # pending, in_progress, completed, overdue
    priority = db.Column(db.String(20), default='normal') # low, normal, high, urgent
    due_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date) # Date when it was actually finished
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    worked_hours = db.Column(db.Numeric(10, 2), default=0)
    estimated_hours = db.Column(db.Numeric(10, 2), default=0)
    actual_hours = db.Column(db.Numeric(10, 2), default=0)
    
    # Collaborators
    collaborators_json = db.Column(db.JSON) 
    # assigned_collaborators was removed since it does not exist in the db schema and is crashing production
    
    notes = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    trigger_type = db.Column(db.String(50), default='manual') # manual, automatic
    
    owner_employee_id = db.Column(db.Integer)
    responsible_id = db.Column(db.Integer)
    executor_id = db.Column(db.Integer)
    
    score_weight = db.Column(db.Numeric(10, 2), default=1.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'process_id': self.process_id,
            'routine_id': self.routine_id,
            'instance_code': self.instance_code,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if hasattr(self.due_date, 'isoformat') else self.due_date,
            'started_at': self.started_at.isoformat() if hasattr(self.started_at, 'isoformat') else self.started_at,
            'completed_at': self.completed_at.isoformat() if hasattr(self.completed_at, 'isoformat') else self.completed_at,
            'worked_hours': float(self.worked_hours or 0),
            'estimated_hours': float(self.estimated_hours or 0),
            'actual_hours': float(self.actual_hours or 0),
            'collaborators_json': self.collaborators_json,
            'notes': self.notes,
            'trigger_type': self.trigger_type,
            'score_weight': float(self.score_weight or 1.0),
            'process_name': self.process_rel.name if self.process_rel else None,
            'process_code': self.process_rel.code if self.process_rel else None
        }

    # Relationships
    process_rel = db.relationship('Process', backref='instances')
    
    # Link to the Schedule (Routine)
    routine = db.relationship('Routine', foreign_keys=[routine_id], backref='instances')

    # View-only link to the Activity (POP) if the IDs happen to match or for legacy support
    pop_routine = db.relationship(
        'ProcessRoutine',
        primaryjoin="ProcessInstance.routine_id==ProcessRoutine.id",
        foreign_keys='ProcessInstance.routine_id',
        viewonly=True
    )

class ProcessInstanceCollaborator(db.Model):
    __tablename__ = 'process_instance_collaborators'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    process_instance_id = db.Column(db.Integer, db.ForeignKey('process_instances.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    role = db.Column(db.String(50), default='executor') # owner, responsible, executor
    estimated_hours = db.Column(db.Numeric(10, 2), default=0)
    worked_hours = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
