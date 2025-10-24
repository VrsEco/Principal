"""
Models para Sistema de Equipes - My Work
"""
from datetime import datetime
from . import db


class Team(db.Model):
    """Equipe de trabalho"""
    __tablename__ = 'teams'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Identificação
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    leader_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    members = db.relationship('TeamMember', backref='team', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Serializa para dicionário"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'leader_id': self.leader_id,
            'is_active': self.is_active,
            'members_count': self.members.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Team {self.name}>'


class TeamMember(db.Model):
    """Membro de equipe"""
    __tablename__ = 'team_members'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Relacionamentos
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    role = db.Column(db.String(50), default='member')  # 'leader', 'member', 'viewer'
    
    # Auditoria
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    left_at = db.Column(db.DateTime)
    
    # Constraint: Usuário não pode estar duplicado na mesma equipe
    __table_args__ = (
        db.UniqueConstraint('team_id', 'employee_id', name='unique_team_member'),
    )
    
    def to_dict(self):
        """Serializa para dicionário"""
        return {
            'id': self.id,
            'team_id': self.team_id,
            'employee_id': self.employee_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'left_at': self.left_at.isoformat() if self.left_at else None
        }
    
    def __repr__(self):
        return f'<TeamMember team={self.team_id} employee={self.employee_id}>'

