from datetime import datetime
from . import db
import json

class AIAgent(db.Model):
    """AI Agent configuration model"""
    __tablename__ = 'ai_agents'
    
    id = db.Column(db.String(100), primary_key=True)  # Unique identifier
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.String(20), default='1.0')
    status = db.Column(db.String(20), default='active')  # active, inactive
    
    # Activation settings
    page = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(100), nullable=False)
    button_text = db.Column(db.String(200), nullable=False)
    
    # Input data configuration
    required_data = db.Column(db.JSON)  # List of required data fields
    optional_data = db.Column(db.JSON)  # List of optional data fields
    
    # Prompt configuration
    prompt_template = db.Column(db.Text)
    
    # Response format configuration
    format_type = db.Column(db.String(20), default='markdown')  # markdown, json, html
    output_field = db.Column(db.String(100), default='ai_insights')
    response_template = db.Column(db.Text)
    
    # Advanced settings
    timeout = db.Column(db.Integer, default=300)
    max_retries = db.Column(db.Integer, default=3)
    execution_mode = db.Column(db.String(20), default='sequential')  # sequential, parallel
    cache_enabled = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'status': self.status,
            'activation': {
                'page': self.page,
                'page_label': self.get_page_label(),
                'section': self.section,
                'section_label': self.get_section_label(),
                'button_text': self.button_text
            },
            'input_data': {
                'required': self.required_data or [],
                'optional': self.optional_data or []
            },
            'prompt_template': self.prompt_template,
            'response_format': {
                'type': self.format_type,
                'output_field': self.output_field,
                'template': self.response_template
            },
            'advanced_settings': {
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'execution_mode': self.execution_mode,
                'cache_enabled': self.cache_enabled
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_page_label(self):
        """Get human-readable page label"""
        labels = {
            'company': 'Dados da Organização',
            'participants': 'Participantes',
            'drivers': 'Direcionadores',
            'okr-global': 'OKRs Globais',
            'okr-area': 'OKRs de Área',
            'projects': 'Projetos',
            'reports': 'Relatórios'
        }
        return labels.get(self.page, self.page)
    
    def get_section_label(self):
        """Get human-readable section label"""
        labels = {
            'analyses': 'Análises',
            'summary': 'Resumo Executivo',
            'interviews': 'Entrevistas',
            'vision': 'Visão',
            'market': 'Mercado',
            'company': 'Empresa'
        }
        return labels.get(self.section, self.section)
    
    def __repr__(self):
        return f'<AIAgent {self.id}: {self.name}>'
