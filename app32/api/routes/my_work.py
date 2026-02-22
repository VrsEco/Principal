from flask import Blueprint, render_template, jsonify, request, send_file
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Company, Employee, Project, ProjectTask, Process, ProcessInstance
from services.pdf_service import PDFGenerator

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
    from models.project import ProjectTask, Project
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
    from services.my_work_service import get_filter_options
    try:
        data = get_filter_options(current_user.id)
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/activities')
@login_required
def my_work_api_activities():
    from services.my_work_service import (
        get_user_activities, get_user_stats,
        get_employee_from_user, get_user_employees,
        _get_company_activities_unrestricted, _calculate_stats_from_activities
    )
    from models.user import User
    from database.postgres_helper import connect as pg_connect
    import traceback

    user = User.query.get(current_user.id)
    user_role = getattr(user, 'role', 'collaborator') if user else 'collaborator'

    employee_id = get_employee_from_user(current_user.id)

    scope = request.args.get('scope', 'me')

    # Parsing filters
    company_ids_str = request.args.get('company_ids')
    company_ids = [int(i) for i in company_ids_str.split(',') if i.strip()] if company_ids_str else None

    responsible_ids_str = request.args.get('responsible_ids')
    responsible_ids = [int(i) for i in responsible_ids_str.split(',') if i.strip()] if responsible_ids_str else None

    executor_ids_str = request.args.get('executor_ids')
    executor_ids = [int(i) for i in executor_ids_str.split(',') if i.strip()] if executor_ids_str else None

    project_ids_str = request.args.get('project_ids')
    project_ids = [int(i) for i in project_ids_str.split(',') if i.strip()] if project_ids_str else None

    process_ids_str = request.args.get('process_ids')
    process_ids = [int(i) for i in process_ids_str.split(',') if i.strip()] if process_ids_str else None

    delivery_tags_str = request.args.get('delivery_tags')
    delivery_tags = [i.strip() for i in delivery_tags_str.split(',') if i.strip()] if delivery_tags_str else None

    filters = {
        "search": request.args.get('search'),
        "sort": request.args.get('sort', 'deadline'),
        "due_date_start": request.args.get('due_date_start'),
        "due_date_end": request.args.get('due_date_end'),
        "delivery_tags": delivery_tags,
        "responsible_ids": responsible_ids,
        "executor_ids": executor_ids,
        "project_ids": project_ids,
        "process_ids": process_ids,
        "project_selection": request.args.get('project_selection'),
        "process_selection": request.args.get('process_selection'),
    }

    try:
        # 1. Definir acesso do usuário (Quais empresas ele pode ver?)
        accessible_company_ids = []
        all_employee_ids = []

        if user_role == 'admin':
            all_companies = Company.query.all()
            accessible_company_ids = [c.id for c in all_companies]
            # Admins podem ter employee_ids em algumas empresas também
            if employee_id:
                user_employees = get_user_employees(current_user.id)
                all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]
        else:
            user_employees = get_user_employees(current_user.id)
            accessible_company_ids = [c['company_id'] for c in user_employees if c.get('company_id')]
            all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]

        if not accessible_company_ids:
            return jsonify({"success": True, "data": [], "stats": {
                "pending": 0, "in_progress": 0, "overdue": 0, "completed": 0
            }})

        # 2. Filtrar apenas pelas empresas que o usuário tem acesso E solicitou
        if company_ids:
            # Garante que o usuário só possa pedir dados das empresas que ele tem acesso
            effective_company_ids = [cid for cid in company_ids if cid in accessible_company_ids]
        else:
            # Se não pediu nenhuma específica, por padrão pega todas que tem acesso,
            # OU pega a empresa principal dele (se as regras de negócio preferirem).
            # Como o usuário pediu que funcionasse com "todas", usaremos todas permitidas.
            effective_company_ids = accessible_company_ids
            
        if not effective_company_ids:
            return jsonify({"success": True, "data": [], "stats": {
                "pending": 0, "in_progress": 0, "overdue": 0, "completed": 0
            }})

        # 3. Chamar o Layer 3 passando explicitamente o array de permissões
        # Verifica se ele não tem employee_id e é admin/client para usar a view de supervisão
        if not employee_id and user_role in ('admin', 'client'):
            # Modo de supervisão pura (não tem pendências próprias)
            conn = pg_connect()
            cursor = conn.cursor()
            try:
                activities = _get_company_activities_unrestricted(
                    cursor, effective_company_ids, filters=filters
                )
                stats = _calculate_stats_from_activities(activities)
            finally:
                conn.close()
            return jsonify({"success": True, "data": activities, "stats": stats})

        # Modo normal (tem pendências próprias nas empresas)
        activities = get_user_activities(
            employee_id,
            scope=scope,
            filters=filters,
            company_ids=effective_company_ids,
            employee_ids=all_employee_ids
        )
        stats = get_user_stats(
            employee_id,
            scope=scope,
            company_ids=effective_company_ids,
            filters=filters,
            employee_ids=all_employee_ids
        )

        return jsonify({
            "success": True,
            "data": activities,
            "stats": stats
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@my_work_bp.route('/my-work/api/occurrences/summary')
@login_required
def my_work_occurrences_summary():
    from services.my_work_service import get_occurrences_summary, get_employee_from_user
    
    employee_id = get_employee_from_user(current_user.id)
    company_ids_str = request.args.get('company_ids')
    company_ids = [int(i) for i in company_ids_str.split(',') if i.strip()] if company_ids_str else None
    
    try:
        summary = get_occurrences_summary(employee_id, company_ids=company_ids)
        return jsonify({
            "success": True,
            "data": summary
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
