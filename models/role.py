from datetime import datetime
from . import db

class Role(db.Model):
    """
    Role Model (Cargo/Função)
    Define a hierarquia e permissões dentro de uma empresa.
    """
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    
    title = db.Column(db.String(100), nullable=False)
    parent_role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True) # Hierarquia de cargos
    reports_to = db.Column(db.String(100)) # Texto descritivo ou ID? No banco parecia ser texto ou ID.
    
    department = db.Column(db.String(100))
    color = db.Column(db.String(20)) # Para organograma
    headcount_planned = db.Column(db.Integer, default=1)
    weekly_hours = db.Column(db.Numeric(5, 2))
    notes = db.Column(db.Text)
    
    # Novo campo para permissões (JSON)
    # Ex: {'financial': 'view', 'tasks': 'edit'}
    permissions = db.Column(db.JSON) 

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # company = db.relationship("Company", backref="roles")
    # parent = db.relationship("Role", remote_side=[id], backref="children")

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "parent_role_id": self.parent_role_id,
            "department": self.department,
            "color": self.color,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Role {self.title}>"
