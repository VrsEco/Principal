from datetime import datetime
from . import db


class Plan(db.Model):
    """
    Central planning model for both Growth and Implantation modes.
    Ensures multi-tenancy via company_id.
    """

    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # 'growth' or 'implantation'
    mode = db.Column(db.String(20), nullable=False, index=True)
    
    # 'draft', 'active', 'archived'
    status = db.Column(db.String(20), default="draft", server_default="draft")
    
    progress = db.Column(db.Integer, default=0, server_default="0")
    
    # Flexible metadata for specific planning data not covered by other tables
    meta_data = db.Column(db.JSON, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    company = db.relationship("Company", back_populates="plans")

    # Relationships
    participants = db.relationship(
        "PlanParticipant", backref="plan", cascade="all, delete-orphan", lazy="dynamic"
    )
    section_statuses = db.relationship(
        "PlanSectionStatus", backref="plan", cascade="all, delete-orphan", lazy="dynamic"
    )
    implantation_data = db.relationship(
        "PlanImplantationData", backref="plan", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "title": self.title,
            "description": self.description,
            "mode": self.mode,
            "status": self.status,
            "progress": self.progress,
            "meta_data": self.meta_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PlanParticipant(db.Model):
    """
    Link between a Plan and a User/Employee.
    """

    __tablename__ = "plan_participants"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    
    # 'owner', 'editor', 'viewer'
    role = db.Column(db.String(20), default="viewer")
    
    # Custom tags or permissions
    meta_data = db.Column(db.JSON, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "employee_id": self.employee_id,
            "role": self.role,
        }

    # Relationships to access names in templates
    user = db.relationship("User", foreign_keys=[user_id])
    employee = db.relationship("Employee", foreign_keys=[employee_id])


class PlanSectionStatus(db.Model):
    """
    Tracks completion status for each section of a plan.
    Example sections: 'drivers', 'okrs', 'finance', etc.
    """

    __tablename__ = "plan_section_status"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    section_key = db.Column(db.String(50), nullable=False)  # e.g., 'growth_drivers'
    
    # 'pending', 'in_progress', 'completed'
    status = db.Column(db.String(20), default="pending")
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "section_key": self.section_key,
            "status": self.status,
            "updated_at": self.updated_at.isoformat(),
        }


class PlanDriver(db.Model):
    """
    Drivers for Growth planning.
    """

    __tablename__ = "plan_drivers"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    
    # 'driver', 'opportunity', 'threat'
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default="medium")
    
    # Linked OKR IDs or other metadata
    meta_data = db.Column(db.JSON, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "type": self.type,
            "description": self.description,
            "priority": self.priority,
            "meta_data": self.meta_data,
        }


class PlanImplantationData(db.Model):
    """
    Polymorphic-like storage for Implementation planning sections.
    """

    __tablename__ = "plan_implantation_data"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    
    # 'alignment', 'market_persona', 'market_value', 'execution_map', etc.
    section_key = db.Column(db.String(50), nullable=False, index=True)
    
    # The actual data for the section
    content = db.Column(db.JSON, nullable=False)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "section_key": self.section_key,
            "content": self.content,
            "updated_at": self.updated_at.isoformat(),
        }
