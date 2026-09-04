from datetime import datetime
from . import db

class Role(db.Model):
    """
    Role Model (Cargo/Função)
    Define a hierarquia e permissões dentro de uma empresa.
    """
    __tablename__ = "roles"
    __table_args__ = (db.UniqueConstraint("company_id", "id", name="uq_roles_company_id"),)

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
    qualification_requirements = db.Column(db.Text, nullable=True)
    
    # Novo campo para permissões (JSON)
    # Ex: {'financial': 'view', 'tasks': 'edit'}
    permissions = db.Column(db.JSON) 

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # company = db.relationship("Company", backref="roles")
    # parent = db.relationship("Role", remote_side=[id], backref="children")

    def to_dict(self):
        # Safe date formatting helper
        def format_dt(dt):
            if dt is None: return None
            try:
                return dt.isoformat()
            except AttributeError:
                return str(dt)

        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "parent_role_id": self.parent_role_id,
            "department": self.department,
            "color": self.color,
            "headcount_planned": self.headcount_planned,
            "qualification_requirements": self.qualification_requirements,
            "permissions": self.permissions,
            "created_at": format_dt(self.created_at),
            "updated_at": format_dt(self.updated_at),
        }

    def __repr__(self):
        return f"<Role {self.title}>"
