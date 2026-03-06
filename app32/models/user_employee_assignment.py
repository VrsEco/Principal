from datetime import datetime
from . import db

class UserEmployeeAssignment(db.Model):
    """
    UserEmployeeAssignment Model (Associação Usuário x Colaborador)
    Gerencia o acesso de um Usuário a uma vaga/posição de Colaborador (Employee) em uma Empresa.
    Permite controle por períodos (start/end dates) para manter histórico e evitar quebras.
    """
    __tablename__ = "user_employee_assignments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    
    start_date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    end_date = db.Column(db.Date, nullable=True) # Se nulo, acesso é permanente/atual
    
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default="active") # active, inactive, pending
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("assignments", lazy="dynamic"))
    employee = db.relationship("Employee", backref=db.backref("assignments", lazy="dynamic"))

    def to_dict(self):
        """Serializa para dicionário."""
        from datetime import date, datetime
        
        def format_date(value):
            if value is None: return None
            if isinstance(value, (date, datetime)): return value.isoformat()
            return str(value)
            
        return {
            "id": self.id,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "start_date": format_date(self.start_date),
            "end_date": format_date(self.end_date),
            "is_active": self.is_active,
            "status": self.status,
            "notes": self.notes,
            "created_at": format_date(self.created_at),
            "updated_at": format_date(self.updated_at)
        }

    def __repr__(self):
        return f"<Assignment User:{self.user_id} -> Employee:{self.employee_id}>"
