from flask import Blueprint, render_template, jsonify, request, send_file
from flask_login import login_required, current_user
from datetime import datetime
from models import db, User, Company, Employee, Project, ProjectTask, Process, ProcessInstance
from services.pdf_service import PDFGenerator
import logging

logger = logging.getLogger(__name__)

my_work_bp = Blueprint('my_work', __name__)

@my_work_bp.route('/my-work')
@login_required
def my_work():
    """My Work dashboard page"""
    return render_template('modules/my_work/my_work_v2.html')

def safe_date_format(dt, format_type='br'):
    """Safely format a date object or string"""
    if not dt:
        return '--' if format_type == 'br' else None
    
    # If it's already a date/datetime object (has strftime)
    if hasattr(dt, 'strftime'):
        if format_type == 'br':
            return dt.strftime('%d/%m/%Y')
        return dt.isoformat()
    
    # If it's a string, try to convert YYYY-MM-DD to DD/MM/YYYY if requested
    if isinstance(dt, str):
        if format_type == 'br' and len(dt) >= 10 and dt[4] == '-' and dt[7] == '-':
            # Simple conversion for YYYY-MM-DD to DD/MM/YYYY
            return f"{dt[8:10]}/{dt[5:7]}/{dt[0:4]}"
        return dt # Return as is
            
    return str(dt)

@my_work_bp.route('/my-work/export-pdf')
@login_required
def export_my_work_pdf():
    """Generates and downloads a PDF report for My Work"""
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        return jsonify({"error": "Employee not found for current user"}), 404
        
    # Fetch tasks
    tasks = ProjectTask.query.filter_by(employee_id=employee.id).all()
    # Fetch process instances
    all_instances = ProcessInstance.query.all()
    relevant_instances = []
    for inst in all_instances:
        collabs = inst.collaborators_json or []
        if any(c.get('id') == employee.id for c in collabs):
            relevant_instances.append(inst)
    
    activities = []
    for t in tasks:
        activities.append({
            "type": "projeto",
            "title": t.what,
            "due_date": safe_date_format(t.due_date, 'br'),
            "status": t.status
        })
    for i in relevant_instances:
        activities.append({
            "type": "processo",
            "title": f"{i.instance_code} - {i.title}",
            "due_date": safe_date_format(i.due_date),
            "status": i.status
        })
        
    stats = {
        "pending": len([a for a in activities if a['status'] in ['pending', 'planned', 'open']]),
        "in_progress": len([a for a in activities if a['status'] == 'in_progress']),
        "overdue": 0,
        "completed": len([a for a in activities if a['status'] in ['completed', 'done']])
    }
    
    pdf_buffer = PDFGenerator.generate_my_work_report(current_user.name or current_user.email, activities, stats)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    )

@my_work_bp.route('/my-work/process-instance/<int:instance_id>')
@login_required
def process_instance_view(instance_id):
    """Detailed view of a process execution"""
    instance = ProcessInstance.query.get_or_404(instance_id)
    company = Company.query.get(instance.company_id)
    return render_template('modules/processes/process_instance_v2.html', 
                          instance=instance, 
                          instance_data=instance.to_dict(),
                          company=company)

@my_work_bp.route('/my-work/project-task/<int:task_id>')
@login_required
def project_task_view(task_id):
    """Detailed view of a project task execution (Hours and Info)"""
    from models import ProjectTask, Project
    task = ProjectTask.query.get_or_404(task_id)
    project = Project.query.get(task.project_id) if task.project_id else None
    company = Company.query.get(project.company_id) if project else None
    return render_template('modules/projects/project_task_v2.html', 
                           task=task, 
                           task_data=task.to_dict(),
                           project=project,
                           company=company)

@my_work_bp.route('/my-work/api/filter-options')
@login_required
def my_work_filter_options():
    from services.my_work.discovery_service import get_filter_options_v2
    try:
        data = get_filter_options_v2(current_user.id)
        logger.info(f"📊 Filter Options Response: {len(data.get('companies', []))} companies, {len(data.get('collaborators', []))} collabs, role={data.get('user_role')}")
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        logger.error(f"filter-options error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/activities')
@login_required
def my_work_api_activities():
    from services.my_work.discovery_service import get_user_activities_v2
    # In v2, stats are calculated directly or derived from data for now
    from services.my_work_service import _calculate_stats_from_activities
    
    # user = User.query.get(current_user.id) # Redundante pois current_user já é o objeto User
    scope = request.args.get('scope', 'me')

    def _parse_ints(val_str):
        if not val_str: return None
        res = []
        for i in val_str.split(','):
            i = i.strip()
            if i and i.isdigit():
                res.append(int(i))
        return res if res else None

    # Parsing filters
    company_ids = _parse_ints(request.args.get('company_ids'))

    # Merge responsible_ids and executor_ids into a single list of employee_ids to filter
    r_ids = _parse_ints(request.args.get('responsible_ids')) or []
    e_ids = _parse_ints(request.args.get('executor_ids')) or []
    all_emp_ids = list(set(r_ids + e_ids))

    # Normalizing request parameters to filters dict
    filters = {
        "search": request.args.get('search'),
        "sort": request.args.get('sort', 'deadline'),
        "project_ids": _parse_ints(request.args.get('project_ids')),
        "process_ids": _parse_ints(request.args.get('process_ids')),
        "employee_ids": all_emp_ids if all_emp_ids else None
    }


    active_company_id = request.args.get('active_company_id', type=int)

    logger.info(f"📊 API Request: scope={scope}, company_ids={company_ids}, active_company={active_company_id}")
    try:
        activities, scope_counts = get_user_activities_v2(
            user_id=current_user.id,
            scope=scope,
            filters=filters,
            company_ids=company_ids,
            active_company_id=active_company_id
        )
        
        stats = _calculate_stats_from_activities(activities)

        return jsonify({
            "success": True,
            "data": activities,
            "stats": stats,
            "scope_counts": scope_counts
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/occurrences/summary')
@login_required
def my_work_occurrences_summary():
    from services.my_work_service import get_occurrences_summary, get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_ids_str = request.args.get('company_ids')
    
    company_ids = None
    if company_ids_str:
        company_ids = []
        for i in company_ids_str.split(','):
            i = i.strip()
            if i and i.isdigit():
                company_ids.append(int(i))
    
    try:
        summary = get_occurrences_summary(employee_id, company_ids=company_ids)
        return jsonify({
            "success": True,
            "data": summary
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/team-overview')
@login_required
def my_work_team_overview():
    from services.my_work_service import get_team_overview, get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_id_str = request.args.get('company_id')
    company_id = int(company_id_str) if company_id_str and company_id_str.isdigit() else None
    
    try:
        data = get_team_overview(employee_id, company_id)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Team Overview Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/company-overview')
@login_required
def my_work_company_overview():
    from services.my_work.metrics_service import get_company_overview_v2
    from services.my_work_service import get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_id_str = request.args.get('company_id')
    company_id = int(company_id_str) if company_id_str and company_id_str.isdigit() else None
    
    try:
        data = get_company_overview_v2(employee_id, company_id)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Company Overview Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
