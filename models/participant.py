from datetime import datetime
from . import db

class Participant(db.Model):
    """Participant model"""
    __tablename__ = 'participants'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.String(100), db.ForeignKey('plans.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100))
    relation = db.Column(db.String(50))  # Acionista, Gestor, Equipe interna
    email = db.Column(db.String(120))
    cpf = db.Column(db.String(14))
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active')  # active, inactive
    message_sent = db.Column(db.Boolean, default=False)
    email_confirmed = db.Column(db.Boolean, default=False)
    whatsapp_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'name': self.name,
            'role': self.role,
            'relation': self.relation,
            'email': self.email,
            'cpf': self.cpf,
            'phone': self.phone,
            'status': self.status,
            'message_sent': self.message_sent,
            'email_confirmed': self.email_confirmed,
            'whatsapp_confirmed': self.whatsapp_confirmed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Participant {self.name}>'
