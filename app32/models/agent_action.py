from datetime import datetime
from . import db
import json

class AgentAction(db.Model):
    """
    Representa uma ação proposta por um agente de IA que requer aprovação humana
    ou um escalonamento entre diferentes squads de agentes.
    """
    __tablename__ = "agent_actions"

    id = db.Column(db.Integer, primary_key=True)
    
    # Tipo de ação: 'technical_fix' (Engenharia), 'business_decision' (Trabalho), 'system_config'
    type = db.Column(db.String(50), nullable=False)
    
    # Status: 'pending', 'approved', 'rejected', 'executed', 'failed'
    status = db.Column(db.String(20), default="pending", nullable=False)
    
    # Agentes envolvidos
    requesting_agent = db.Column(db.String(100), nullable=False)  # ex: 'sapiens'
    handling_agent = db.Column(db.String(100))                   # ex: '@QA_AUTOMATION'
    
    # Descrição para o usuário
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Dados técnicos da ação (JSON)
    # Ex: {"file": "...", "patch": "...", "impact": "..."}
    payload = db.Column(db.JSON)
    
    # Checkpoints para Rollback (@QA_AUTOMATION Requirement)
    original_file = db.Column(db.String(255))
    backup_content = db.Column(db.Text)
    
    # Contexto de Multi-tenancy
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Usuário que deve aprovar
    
    # Feedback do usuário
    user_feedback = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime)
    executed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "requesting_agent": self.requesting_agent,
            "handling_agent": self.handling_agent,
            "title": self.title,
            "description": self.description,
            "payload": self.payload,
            "company_id": self.company_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def __repr__(self):
        return f"<AgentAction {self.id}: {self.type} - {self.status}>"
