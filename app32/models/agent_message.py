from datetime import datetime
from . import db

class AgentMessage(db.Model):
    """
    Model to store communication logs between Users and Agents.
    Includes emails, messenger chats, and internal platform chats.
    """
    __tablename__ = 'agent_messages'

    id = db.Column(db.Integer, primary_key=True)
    
    # Context
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Optional if system-initiated
    
    # Agent identification
    agent_type = db.Column(db.String(50), nullable=False) # e.g., 'planejamento', 'cadastro', 'externo'
    agent_name = db.Column(db.String(100)) # e.g. 'Agente PEV'
    
    # Message Content
    direction = db.Column(db.String(20), nullable=False) # 'inbound' (User->Agent) or 'outbound' (Agent->User)
    channel = db.Column(db.String(50), default='platform') # platform, email, whatsapp, slack
    content = db.Column(db.Text, nullable=False)
    
    # Metadata
    tokens_used = db.Column(db.Integer, default=0)
    model_used = db.Column(db.String(100)) # e.g. 'gpt-4'
    metadata_json = db.Column(db.JSON, default={}) # Extra info
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Specific for external tracking
    external_id = db.Column(db.String(100)) # Message ID from external provider (e.g. Gmail ID)
    
    # Relationships
    company = db.relationship('Company', backref='agent_messages')
    user = db.relationship('User', backref='agent_messages')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'agent_type': self.agent_type,
            'agent_name': self.agent_name,
            'direction': self.direction,
            'channel': self.channel,
            'content': self.content,
            'created_at': self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            'metadata': self.metadata_json
        }
