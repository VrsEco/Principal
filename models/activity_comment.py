"""
Model para Comentários em Atividades - My Work
"""
from datetime import datetime
from . import db


class ActivityComment(db.Model):
    """Comentários e anotações em atividades"""
    __tablename__ = 'activity_comments'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Referência polimórfica à atividade
    activity_type = db.Column(db.String(20), nullable=False)  # 'project' ou 'process'
    activity_id = db.Column(db.Integer, nullable=False)
    
    # Autor
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    employee_name = db.Column(db.String(200))  # Cache
    
    # Conteúdo
    comment_type = db.Column(db.String(20))  # 'note', 'progress', 'issue', 'solution', 'question'
    comment_text = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False, nullable=False)
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Serializa para dicionário"""
        return {
            'id': self.id,
            'activity_type': self.activity_type,
            'activity_id': self.activity_id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'comment_type': self.comment_type,
            'comment_text': self.comment_text,
            'is_private': self.is_private,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ActivityComment {self.activity_type}:{self.activity_id} by {self.employee_name}>'

