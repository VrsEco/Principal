from datetime import datetime
from . import db

class Employee(db.Model):
    """
    Employee Model (Colaborador)
    Representa o vínculo entre um Usuário e uma Empresa.
    Um usuário pode ter múltiplos registros de Employee (um por empresa).
    """
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True) # Pode ser nulo se for um funcionário sem acesso ao sistema
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="active") # active, inactive, vacation
    weekly_hours = db.Column(db.Numeric(5, 2))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraint: Um usuário não pode ter dois vínculos com a mesma empresa
    # Mas pode ter vínculos com empresas diferentes
    __table_args__ = (
        db.UniqueConstraint('user_id', 'company_id', name='idx_employees_user_company_unique'),
    )

    # Relationships
    # user = db.relationship("User", backref="employees") # Definido no User ou aqui? Geralmente backref resolve.
    # company = db.relationship("Company", backref="employees")
    # role = db.relationship("Role", backref="employees")

    def to_dict(self):
        """Serializa Employee para dicionário."""
        from datetime import date, datetime
        
        # Helper para formatar datas
        def format_date(value):
            if value is None:
                return None
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            if isinstance(value, str):
                return value  # Já é string, retornar como está
            return str(value)
        
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "department": self.department,
            "hire_date": format_date(self.hire_date),
            "status": self.status,
            "weekly_hours": float(self.weekly_hours) if self.weekly_hours else None,
            "created_at": format_date(self.created_at),
            "updated_at": format_date(getattr(self, 'updated_at', None)),
        }

    def __repr__(self):
        return f"<Employee {self.name} @ {self.company_id}>"
