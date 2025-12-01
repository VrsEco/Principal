from sqlalchemy import func
from . import db


class AppComplianceReport(db.Model):
    __tablename__ = "app_compliance_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    scope = db.Column(db.String(32), nullable=False)
    requested_code = db.Column(db.String(16))
    total_pages = db.Column(db.Integer, nullable=False, default=0)
    ok_count = db.Column(db.Integer, nullable=False, default=0)
    warn_count = db.Column(db.Integer, nullable=False, default=0)
    fail_count = db.Column(db.Integer, nullable=False, default=0)
    generated_at = db.Column(db.DateTime, nullable=False, server_default=func.now())
    overview = db.Column(db.JSON)

    items = db.relationship(
        "AppComplianceReportItem",
        back_populates="report",
        cascade="all, delete-orphan",
    )


class AppComplianceReportItem(db.Model):
    __tablename__ = "app_compliance_report_items"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("app_compliance_reports.id"), nullable=False)
    page_code = db.Column(db.String(16))
    page_name = db.Column(db.String(256))
    page_route = db.Column(db.String(256))
    status = db.Column(db.String(16), nullable=False)
    primary_issue = db.Column(db.String(512))
    checks = db.Column(db.JSON)

    report = db.relationship("AppComplianceReport", back_populates="items")
