"""
Model para Registro de Horas Trabalhadas - My Work
"""
from datetime import datetime, date
from . import db


class ActivityWorkLog(db.Model):
    """Registro de horas trabalhadas em atividades"""
    __tablename__ = 'activity_work_logs'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Referência polimórfica à atividade
    activity_type = db.Column(db.String(20), nullable=False)  # 'project' ou 'process'
    activity_id = db.Column(db.Integer, nullable=False)
    
    # Quem trabalhou
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    employee_name = db.Column(db.String(200))  # Cache para histórico
    
    # Detalhes do trabalho
    work_date = db.Column(db.Date, nullable=False, default=date.today)
    hours_worked = db.Column(db.Numeric(5, 2), nullable=False)  # Ex: 2.5 = 2h 30min
    description = db.Column(db.Text)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Serializa para dicionário"""
        return {
            'id': self.id,
            'activity_type': self.activity_type,
            'activity_id': self.activity_id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'work_date': self.work_date.isoformat() if self.work_date else None,
            'hours_worked': float(self.hours_worked) if self.hours_worked else 0,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<ActivityWorkLog {self.activity_type}:{self.activity_id} {self.hours_worked}h>'

