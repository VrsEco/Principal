from datetime import datetime
from . import db


class CompanyData(db.Model):
    """Company data model for specific plan"""

    __tablename__ = "company_data"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    trade_name = db.Column(db.String(200))
    legal_name = db.Column(db.String(200))
    cnpj = db.Column(db.String(18))
    coverage_physical = db.Column(db.String(50))
    coverage_online = db.Column(db.String(50))
    experience_total = db.Column(db.String(50))
    experience_segment = db.Column(db.String(50))
    cnaes = db.Column(db.JSON)  # List of CNAE codes
    headcount_strategic = db.Column(db.Integer, default=0)
    headcount_tactical = db.Column(db.Integer, default=0)
    headcount_operational = db.Column(db.Integer, default=0)
    mission = db.Column(db.Text)
    vision = db.Column(db.Text)
    values = db.Column(db.Text)
    process_map_file = db.Column(db.String(255))
    org_chart_file = db.Column(db.String(255))
    ai_insights = db.Column(db.Text)
    consultant_analysis = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    financial_data = db.relationship(
        "FinancialData",
        backref="company_data",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "trade_name": self.trade_name,
            "legal_name": self.legal_name,
            "cnpj": self.cnpj,
            "coverage_physical": self.coverage_physical,
            "coverage_online": self.coverage_online,
            "experience_total": self.experience_total,
            "experience_segment": self.experience_segment,
            "cnaes": self.cnaes,
            "headcount_strategic": self.headcount_strategic,
            "headcount_tactical": self.headcount_tactical,
            "headcount_operational": self.headcount_operational,
            "mission": self.mission,
            "vision": self.vision,
            "values": self.values,
            "process_map_file": self.process_map_file,
            "org_chart_file": self.org_chart_file,
            "ai_insights": self.ai_insights,
            "consultant_analysis": self.consultant_analysis,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<CompanyData {self.plan_id}>"


class FinancialData(db.Model):
    """Financial data model"""

    __tablename__ = "financial_data"

    id = db.Column(db.Integer, primary_key=True)
    company_data_id = db.Column(
        db.Integer, db.ForeignKey("company_data.id"), nullable=False
    )
    line_name = db.Column(db.String(200), nullable=False)
    revenue = db.Column(db.String(100))  # e.g., "R$ 8,2 mi"
    margin = db.Column(db.String(50))  # e.g., "21%"
    market_info = db.Column(db.Text)  # Market size, competition info
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "company_data_id": self.company_data_id,
            "line_name": self.line_name,
            "revenue": self.revenue,
            "margin": self.margin,
            "market_info": self.market_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FinancialData {self.line_name}>"
