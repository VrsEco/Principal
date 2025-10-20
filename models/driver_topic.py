from datetime import datetime
from . import db

class DriverTopic(db.Model):
    """Driver topic model"""
    __tablename__ = 'driver_topics'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.String(100), db.ForeignKey('plans.id'), nullable=False)
    topic_type = db.Column(db.String(50), nullable=False)  # interviews, vision-socios, market, company
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300))
    overall_maturity = db.Column(db.Float)  # 0-5 scale
    maturity_updated_at = db.Column(db.DateTime)
    maturity_suggestion = db.Column(db.Text)
    overall_analysis = db.Column(db.Text)
    analysis_suggestion = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    items = db.relationship('DriverItem', backref='driver_topic', lazy='dynamic', cascade='all, delete-orphan')
    records = db.relationship('DriverRecord', backref='driver_topic', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'topic_type': self.topic_type,
            'title': self.title,
            'subtitle': self.subtitle,
            'overall_maturity': self.overall_maturity,
            'maturity_updated_at': self.maturity_updated_at.isoformat() if self.maturity_updated_at else None,
            'maturity_suggestion': self.maturity_suggestion,
            'overall_analysis': self.overall_analysis,
            'analysis_suggestion': self.analysis_suggestion,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<DriverTopic {self.title}>'

class DriverItem(db.Model):
    """Driver item model"""
    __tablename__ = 'driver_items'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_topic_id = db.Column(db.Integer, db.ForeignKey('driver_topics.id'), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    information = db.Column(db.Text)
    maturity = db.Column(db.Float)  # 0-5 scale
    analysis = db.Column(db.Text)
    alignment = db.Column(db.Text)
    preliminary_plan = db.Column(db.Text)
    final_plan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'driver_topic_id': self.driver_topic_id,
            'prompt': self.prompt,
            'information': self.information,
            'maturity': self.maturity,
            'analysis': self.analysis,
            'alignment': self.alignment,
            'preliminary_plan': self.preliminary_plan,
            'final_plan': self.final_plan,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<DriverItem {self.prompt[:50]}...>'

class DriverRecord(db.Model):
    """Driver record model"""
    __tablename__ = 'driver_records'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_topic_id = db.Column(db.Integer, db.ForeignKey('driver_topics.id'), nullable=False)
    participant_name = db.Column(db.String(200))
    consultant_name = db.Column(db.String(200))
    date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'driver_topic_id': self.driver_topic_id,
            'participant_name': self.participant_name,
            'consultant_name': self.consultant_name,
            'date': self.date.isoformat() if self.date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<DriverRecord {self.participant_name}>'
