from datetime import datetime
from . import db


class EmployeeQualificationEvidence(db.Model):
    """Evidência declarada ou comprovada; ausência não significa reprovação."""
    __tablename__ = 'employee_qualification_evidences'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    employee_id = db.Column(db.Integer, nullable=False)
    qualification_name = db.Column(db.String(255), nullable=False)
    level = db.Column(db.String(80), nullable=True)
    evidence_source = db.Column(db.String(30), nullable=False, default='declared')
    evidence_reference = db.Column(db.String(500), nullable=True)
    expires_on = db.Column(db.Date, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        db.ForeignKeyConstraint(['company_id', 'employee_id'], ['employees.company_id', 'employees.id'], name='fk_qualification_tenant_employee'),
        db.CheckConstraint("evidence_source IN ('declared', 'documented', 'verified')", name='ck_qualification_source'),
        db.UniqueConstraint('company_id', 'employee_id', 'qualification_name', 'level', name='uq_employee_qualification'),
        db.Index('ix_qualification_company_employee', 'company_id', 'employee_id'),
    )

    def to_dict(self):
        return {'id': self.id, 'company_id': self.company_id, 'employee_id': self.employee_id,
                'qualification_name': self.qualification_name, 'level': self.level,
                'evidence_source': self.evidence_source, 'evidence_reference': self.evidence_reference,
                'expires_on': self.expires_on.isoformat() if self.expires_on else None}
