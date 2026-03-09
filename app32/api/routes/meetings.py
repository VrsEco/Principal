from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for, abort
from flask_login import current_user, login_required
from models import Company, Meeting, MeetingAgendaItem, Employee, Project, db
from utils.permissions import permission_required

meetings_bp = Blueprint('meetings', __name__)


def user_can_access_company(company_id):
    if not company_id or not current_user.is_authenticated:
        return False
    company = Company.query.get(company_id)
    if not company or not bool(getattr(company, 'is_active', True)):
        return False
    if str(getattr(current_user, 'role', '')).lower() == 'admin':
        return True
    employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()
    return employee is not None

def get_active_company():
    company_id = session.get('active_company_id')
    if company_id and user_can_access_company(company_id):
        return Company.query.get(company_id)

    if company_id and not user_can_access_company(company_id):
        session.pop('active_company_id', None)

    if current_user.is_authenticated:
        emp = Employee.query.filter_by(user_id=current_user.id, status='active').order_by(Employee.id.asc()).first()
        if emp and user_can_access_company(emp.company_id):
            session['active_company_id'] = emp.company_id
            return Company.query.get(emp.company_id)
        if current_user.role == 'admin':
            first = Company.query.filter_by(is_active=True).order_by(Company.id).first()
            if first:
                session['active_company_id'] = first.id
                return first

    return None

@meetings_bp.route('/')
@login_required
def meetings_manage_root():
    """Redirect to specific company meeting page or show error"""
    company = get_active_company()
    if not company:
        return render_template('404.html'), 404
    return redirect(url_for('meetings.meetings_company_manage', company_id=company.id))

@meetings_bp.route('/company/<int:company_id>')
@login_required
def meetings_company_manage(company_id):
    """Main meeting management page for APP32"""
    if not user_can_access_company(company_id):
        abort(403)

    company = Company.query.get_or_404(company_id)
    
    # Save active company to session
    session['active_company_id'] = company_id
    
    # Fetch meetings (using model)
    meetings = Meeting.query.filter_by(company_id=company_id).order_by(Meeting.created_at.desc()).all()
    meetings_data = [m.to_dict() for m in meetings]
    
    # Fetch employees
    employees = Employee.query.filter_by(company_id=company_id, status='active').all()
    employees_data = [e.to_dict() for e in employees]
    
    # Fetch reusable agenda items
    agenda_items = MeetingAgendaItem.query.filter_by(company_id=company_id).all()
    agenda_items_data = [a.to_dict() for a in agenda_items]
    
    # Fetch projects
    projects = Project.query.filter_by(company_id=company_id).all()
    projects_data = [p.to_dict() for p in projects]

    return render_template(
        "meetings_manage.html",
        company=company.to_dict(),
        meetings=meetings_data,
        employees=employees_data,
        agenda_items=agenda_items_data,
        projects=projects_data,
        active_id="meetings-manage",
    )

@meetings_bp.route('/company/<int:company_id>/meeting/<int:meeting_id>/report')
@login_required
def meeting_report(company_id, meeting_id):
    """Render meeting report/minutes"""
    from datetime import datetime
    if not user_can_access_company(company_id):
        abort(403)
    meeting = Meeting.query.filter_by(id=meeting_id, company_id=company_id).first_or_404()
    company = Company.query.get_or_404(company_id)
    return render_template(
        'report_pdf.html', 
        meeting=meeting.to_dict(), 
        company=company.to_dict(),
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M")
    )
