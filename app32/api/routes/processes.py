import os

from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app, session, redirect, url_for, abort
from flask_login import current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from database import get_db
from models import db, Company, Process, ProcessInstance, Employee
from utils.permissions import permission_required, has_permission

processes_bp = Blueprint('processes', __name__)


def _get_process_with_access(process_id: int, action: str = 'view') -> Process:
    process = Process.query.get_or_404(process_id)

    if not current_user.is_authenticated:
        abort(403, description="Usuário não autenticado.")

    if current_user.role != 'admin' and not has_permission(process.company_id, 'processes', action):
        abort(403, description=f"Permission denied: {action} on processes")

    session['active_company_id'] = process.company_id
    return process

@processes_bp.route('/api/processes/upload-flow', methods=['POST'])
def upload_process_flow():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], 'process_flows', filename))
        return jsonify({"success": True, "filename": filename}), 200

@processes_bp.route('/processes')
@permission_required('processes', 'view')
def processes_list():
    """Processes list page"""
    if current_user.role != 'admin':
        company_id = session.get('active_company_id')
        if not company_id:
            emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
            if emp: company_id = emp.company_id
        
        if company_id:
            # Check if superuser
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
            if not employee or not employee.role or employee.role.title.lower() != 'superuser':
                abort(403, description="Acesso negado: Colaboradores não podem acessar a listagem detalhada de processos.")

    company_id = request.args.get('company_id', type=int) or session.get('active_company_id')
    if not company_id and current_user.is_authenticated:
        if current_user.role == 'admin':
            first = Company.query.order_by(Company.id).first()
            if first:
                company_id = first.id
        else:
            from models import Employee
            emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
            if emp:
                company_id = emp.company_id
    if company_id:
        session['active_company_id'] = company_id
    return render_template('modules/processes/processes_v2.html', company_id=company_id)

@processes_bp.route('/process-map')
@permission_required('processes', 'view')
def process_map():
    """Process map (Big Picture)"""
    from flask_login import current_user

    arg_company_id = request.args.get('company_id', type=int)
    company_id = arg_company_id or session.get('active_company_id')

    # Fallback: pega a primeira empresa permitida para o usuário
    if not company_id and current_user.is_authenticated:
        if current_user.role == 'admin':
            first = Company.query.order_by(Company.id).first()
            if first:
                company_id = first.id
        else:
            from models import Employee
            emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
            if emp:
                company_id = emp.company_id
    
    is_collaborator = False
    if current_user.role != 'admin':
        employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
        if not employee or not employee.role or employee.role.title.lower() != 'superuser':
            is_collaborator = True

    return render_template('modules/processes/process_map_v2.html', 
                           company_id=company_id, 
                           is_collaborator=is_collaborator)

@processes_bp.route('/process-map/compact')
@permission_required('processes', 'view')
def process_map_compact():
    """Print-friendly Compact Process Map (MP-2)"""
    # Use company_id from query params or session
    arg_id = request.args.get('company_id')
    company_id = request.args.get('company_id', type=int) or session.get('active_company_id')
    
    print(f"[DEBUG] MP-2 View Request - arg_id: {arg_id}, session_id: {session.get('active_company_id')}, final_id: {company_id}")
    
    if not company_id:
        return "Nenhuma empresa ativa selecionada.", 400
        
    area_id = request.args.get('area_id', type=int)
    macro_id = request.args.get('macro_id', type=int)
        
    db_helper = get_db()
    company = Company.query.get(company_id)
    if not company:
        return f"Empresa com ID {company_id} não encontrada.", 404
        
    map_data = db_helper.get_process_map(company_id)
    
    # Apply filters if provided
    if area_id:
        map_data['areas'] = [a for a in map_data.get('areas', []) if a['id'] == area_id]
    if macro_id:
        for area in map_data.get('areas', []):
            area['macros'] = [m for m in area.get('macros', []) if m['id'] == macro_id]
    
    # Helper for colors
    def get_stage_color(stage):
        colors = {
            'inbox': '#cbd5e1', 'designing': '#93c5fd', 'deploying': '#3b82f6',
            'stabilizing': '#a855f7', 'stable': '#6366f1'
        }
        return colors.get(stage, '#cbd5e1')

    def get_perf_color(perf):
        colors = {
            'critical': '#ef4444', 'below': '#f59e0b', 'satisfactory': '#10b981'
        }
        return colors.get(perf, '#f1f5f9')

    # Enrich data with colors and formatted names for the template
    for area in map_data.get('areas', []):
        area['display_name'] = f"{area.get('code', '')} - {area.get('name', '')}" if area.get('code') else area.get('name', '')
        
        for macro in area.get('macros', []):
            macro['display_name'] = f"{macro.get('code', '')} - {macro.get('name', '')}" if macro.get('code') else macro.get('name', '')
            
            for p in macro.get('processes', []):
                p['display_name'] = f"{p.get('code', '')} - {p.get('name', '')}" if p.get('code') else p.get('name', '')
                p['stage_color'] = get_stage_color(p.get('kanban_stage'))
                p['perf_color'] = get_perf_color(p.get('performance_level'))

    is_collaborator = False
    if current_user.role != 'admin':
        employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
        if not employee or not employee.role or employee.role.title.lower() != 'superuser':
            is_collaborator = True

    return render_template(
        'modules/processes/process_map_compact_view.html',
        company_name=company.name if company else "Empresa",
        areas=map_data.get('areas', []),
        now=datetime.now().strftime('%d/%m/%Y %H:%M'),
        is_collaborator=is_collaborator
    )

@processes_bp.route('/processes/<int:process_id>')
@permission_required('processes', 'view')
def process_details(process_id):
    """Process details page (modeling/pops)"""
    if current_user.role != 'admin':
        process = Process.query.get_or_404(process_id)
        employee = Employee.query.filter_by(user_id=current_user.id, company_id=process.company_id).first()
        if not employee or not employee.role or employee.role.title.lower() != 'superuser':
            abort(403, description="Acesso negado: Colaboradores não podem acessar os detalhes de modelagem do processo.")

    process = _get_process_with_access(process_id, action='view')
    company = Company.query.get_or_404(process.company_id)
    return render_template('modules/processes/process_details_v2.html', 
                            process_id=process_id, 
                            process=process,
                            company=company)

# --- Process Routines Page and APIs ---

@processes_bp.route('/process-routines')
@permission_required('processes', 'view')
def process_routines_redirect():
    """Redirect to the routine page of the active company."""
    company_id = session.get('active_company_id')
    if not company_id:
        from flask_login import current_user
        from models import Employee
        emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
        if emp:
            company_id = emp.company_id
            session['active_company_id'] = company_id
    
    if company_id:
        return redirect(url_for('processes.process_routines_page', company_id=company_id))
    
    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/process-instances')
@permission_required('processes', 'view')
def process_instances_redirect():
    """Redirect to the instances page of the active company."""
    company_id = session.get('active_company_id')
    if not company_id:
        from flask_login import current_user
        from models import Employee
        emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
        if emp:
            company_id = emp.company_id
            session['active_company_id'] = company_id
    
    if company_id:
        return redirect(url_for('processes.process_instances_page', company_id=company_id))
    
    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/companies/<int:company_id>/process-instances')
@permission_required('processes', 'view')
def process_instances_page(company_id):
    """Render the process instances management page."""
    company = Company.query.get_or_404(company_id)
    return render_template('modules/processes/process_instances_list.html', company=company)

@processes_bp.route('/process-occurrences')
@permission_required('processes', 'view')
def process_occurrences_redirect():
    """Redirect to the occurrences page of the active company."""
    company_id = session.get('active_company_id')
    if not company_id:
        from flask_login import current_user
        from models import Employee
        emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
        if emp:
            company_id = emp.company_id
            session['active_company_id'] = company_id
    
    if company_id:
        return redirect(url_for('processes.process_occurrences_page', company_id=company_id))
    
    return redirect(url_for('my_work.my_work'))

@processes_bp.route('/companies/<int:company_id>/process-occurrences')
@permission_required('processes', 'view')
def process_occurrences_page(company_id):
    """Render the process occurrences management page."""
    company = Company.query.get_or_404(company_id)
    return render_template('modules/processes/process_occurrences_list.html', company=company)

@processes_bp.route('/companies/<int:company_id>/process-routines')
@permission_required('processes', 'view')
def process_routines_page(company_id):
    """Render the process routines management page."""
    company = Company.query.get_or_404(company_id)
    return render_template('process_routines.html', company=company)

@processes_bp.route('/companies/<int:company_id>/process-routines/analysis')
@permission_required('processes', 'view')
def process_routines_analysis_page(company_id):
    """Render analytical page for routine capacity and commitments."""
    from services.routine_analysis_service import get_routine_analysis

    company = Company.query.get_or_404(company_id)
    analysis = get_routine_analysis(company_id)
    return render_template('modules/processes/routine_analysis.html', company=company, analysis=analysis)

@processes_bp.route('/api/companies/<int:company_id>/process-routines/analysis', methods=['GET'])
@permission_required('processes', 'view')
def api_get_process_routines_analysis(company_id):
    """Return analytical payload for routine capacity and commitments."""
    from services.routine_analysis_service import get_routine_analysis

    try:
        return jsonify({"success": True, "data": get_routine_analysis(company_id)})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines', methods=['GET'])
@permission_required('processes', 'view')
def api_get_process_routines(company_id):
    """Get all process routines for a company with collaborator summary"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                r.id,
                r.name,
                r.description,
                r.process_id,
                r.schedule_type,
                r.schedule_value,
                r.deadline_days,
                r.deadline_hours,
                r.deadline_date,
                p.code AS process_code,
                p.name AS process_name,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'employee_id', rc.employee_id,
                            'employee_name', e.name,
                            'hours_used', rc.hours_used,
                            'notes', rc.notes
                        )
                        ORDER BY e.name
                    )
                    FILTER (WHERE rc.employee_id IS NOT NULL),
                    '[]'::json
                ) AS collaborators
            FROM routines r
            LEFT JOIN processes p ON r.process_id = p.id
            LEFT JOIN routine_collaborators rc ON rc.routine_id = r.id
            LEFT JOIN employees e ON e.id = rc.employee_id
            WHERE r.company_id = %s AND (r.is_active = TRUE OR r.is_active IS NULL)
            GROUP BY
                r.id,
                r.name,
                r.description,
                r.process_id,
                r.schedule_type,
                r.schedule_value,
                r.deadline_days,
                r.deadline_hours,
                r.deadline_date,
                p.code,
                p.name
            ORDER BY r.created_at DESC
        """,
            (company_id,),
        )
        
        rows = cursor.fetchall()
        routines = [dict(row) for row in rows]
        conn.close()
        return jsonify({"success": True, "routines": routines})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines', methods=['POST'])
@permission_required('processes', 'create')
def api_create_process_routine(company_id):
    """Create a new process routine"""
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "message": "Nome é obrigatório"}), 400

        process_id = data.get("process_id")
        # process_id could be optional but usually required for "process routines"
        
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO routines (
                company_id, name, description, process_id,
                schedule_type, schedule_value, deadline_days, deadline_hours, deadline_date,
                score_weight, is_active, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """,
            (
                company_id,
                name,
                data.get("description", ""),
                process_id,
                data.get("schedule_type", "weekly"),
                data.get("schedule_value"),
                data.get("deadline_days", 0),
                data.get("deadline_hours", 0),
                data.get("deadline_date"),
                data.get("score_weight", 1.0)
            ),
        )

        routine_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({
            "success": True, 
            "routine_id": routine_id,
            "message": "Rotina cadastrada com sucesso"
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines/<int:routine_id>', methods=['PUT'])
@permission_required('processes', 'edit')
def api_update_process_routine(company_id, routine_id):
    """Update an existing process routine"""
    try:
        data = request.get_json(silent=True) or {}
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE routines SET
                name = %s,
                description = %s,
                process_id = %s,
                schedule_type = %s,
                schedule_value = %s,
                deadline_days = %s,
                deadline_hours = %s,
                score_weight = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND company_id = %s
        """,
            (
                data.get("name"),
                data.get("description", ""),
                data.get("process_id"),
                data.get("schedule_type"),
                data.get("schedule_value"),
                data.get("deadline_days", 0),
                data.get("deadline_hours", 0),
                data.get("score_weight", 1.0),
                routine_id,
                company_id,
            ),
        )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Rotina atualizada com sucesso"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@processes_bp.route('/api/companies/<int:company_id>/process-routines/<int:routine_id>', methods=['DELETE'])
@permission_required('processes', 'delete')
def api_delete_process_routine(company_id, routine_id):
    """Soft delete a process routine"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE routines SET is_active = FALSE WHERE id = %s AND company_id = %s",
            (routine_id, company_id),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Rotina excluída com sucesso"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators', methods=['GET'])
@permission_required('processes', 'view')
def api_get_routine_collaborators(routine_id):
    """Get all collaborators for a routine"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT rc.*, e.name as employee_name, e.email as employee_email
            FROM routine_collaborators rc
            JOIN employees e ON rc.employee_id = e.id
            WHERE rc.routine_id = %s
            ORDER BY e.name
        """,
            (routine_id,),
        )

        collaborators = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "collaborators": collaborators})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators', methods=['POST'])
@permission_required('processes', 'edit')
def api_add_routine_collaborator(routine_id):
    """Add a collaborator to a routine"""
    try:
        data = request.get_json(silent=True) or {}
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO routine_collaborators (routine_id, employee_id, hours_used, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """,
            (
                routine_id,
                data.get("employee_id"),
                data.get("hours_used"),
                data.get("notes", ""),
            ),
        )

        collaborator_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": collaborator_id, "message": "Colaborador adicionado com sucesso"}), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>', methods=['PUT'])
@permission_required('processes', 'edit')
def api_update_routine_collaborator(routine_id, collaborator_id):
    """Update a routine collaborator"""
    try:
        data = request.get_json(silent=True) or {}
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE routine_collaborators
            SET employee_id = %s,
                hours_used = %s,
                notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND routine_id = %s
        """,
            (
                data.get("employee_id"),
                data.get("hours_used"),
                data.get("notes", ""),
                collaborator_id,
                routine_id,
            ),
        )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Colaborador atualizado com sucesso"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@processes_bp.route('/api/routines/<int:routine_id>/collaborators/<int:collaborator_id>', methods=['DELETE'])
@permission_required('processes', 'edit')
def api_delete_routine_collaborator(routine_id, collaborator_id):
    """Delete a routine collaborator"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM routine_collaborators WHERE id = %s AND routine_id = %s",
            (collaborator_id, routine_id),
        )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Colaborador removido com sucesso"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



@processes_bp.route('/api/companies/<int:company_id>/employees')
@permission_required('companies', 'view')
def api_get_company_employees(company_id):
    """Get all employees for a company"""
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, email FROM employees WHERE company_id = %s AND status = 'active' ORDER BY name",
            (company_id,),
        )

        employees = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "employees": employees})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@processes_bp.route('/companies/<int:company_id>/routines/<routine_id>')
@permission_required('processes', 'view')
def routine_details_page(company_id, routine_id):
    """Routine details/creation page"""
    from flask import abort
    company = Company.query.get_or_404(company_id)
    
    pg = get_db()
    conn = pg._get_connection()
    cursor = conn.cursor()

    # Buscar todos os processos para o select
    cursor.execute(
        "SELECT id, code, name FROM processes WHERE company_id = %s AND (is_active = True OR is_active IS NULL) ORDER BY code",
        (company_id,),
    )
    processes = [dict(row) for row in cursor.fetchall()]

    is_new = routine_id == "new"
    if is_new:
        routine = {
            "id": None, "name": "", "description": "", "process_id": None,
            "schedule_type": "weekly", "schedule_value": "",
            "deadline_days": 0, "deadline_hours": 0, "score_weight": 1.0
        }
    else:
        cursor.execute(
            """
            SELECT r.*, p.code as process_code, p.name as process_name
            FROM routines r
            LEFT JOIN processes p ON r.process_id = p.id
            WHERE r.id = %s AND r.company_id = %s
        """,
            (int(routine_id), company_id),
        )
        row = cursor.fetchone()
        if row:
            routine = dict(row)
        else:
            conn.close()
            abort(404)

    conn.close()

    return render_template(
        "routine_details.html",
        company=company,
        routine=routine,
        processes=processes,
        is_new=is_new
    )
