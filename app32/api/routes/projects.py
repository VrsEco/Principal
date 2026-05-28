from flask import Blueprint, render_template, session, jsonify, abort, request, send_file, url_for
from models import Company
from flask_login import current_user

from utils.permissions import get_default_company_id, permission_required, has_company_full_access, is_collaborator_in_company, has_permission, can_manage_project_tasks, can_create_projects

projects_bp = Blueprint('projects', __name__)

def _get_project_page_with_access(project_id):
    from models import Project, Company
    from api.resources.project import apply_project_employee_filter

    company = get_active_company()
    company_id = company.id if company else None

    if company_id:
        query = Project.query.filter_by(id=project_id, company_id=company_id)
        query = apply_project_employee_filter(query, company_id)
        project = query.first()
        if project:
            return project, company

    base_project = Project.query.filter_by(id=project_id).first_or_404()
    fallback_company_id = base_project.company_id

    if not has_permission(fallback_company_id, 'projects', 'view'):
        abort(403, description='Acesso negado ao projeto solicitado.')

    query = Project.query.filter_by(id=project_id, company_id=fallback_company_id)
    query = apply_project_employee_filter(query, fallback_company_id)
    project = query.first_or_404()

    fallback_company = Company.query.get(fallback_company_id)
    if fallback_company:
        session['active_company_id'] = fallback_company.id

    return project, fallback_company

def get_active_company():
    from models import Employee, Company
    import logging
    
    company_id = session.get('active_company_id')
    logging.debug(f"[get_active_company] Initial Session ID: {company_id}")

    if not company_id and current_user.is_authenticated:
        emp = Employee.query.filter_by(user_id=current_user.id, status='active').first()
        if emp:
            company_id = emp.company_id
        else:
            company_id = get_default_company_id()
        
        if company_id:
            session['active_company_id'] = company_id
            logging.debug(f"[get_active_company] Fallback set company_id to: {company_id}")
    
    if company_id:
        res = Company.query.get(company_id)
        return res
        
    return None

@projects_bp.route('/projects')
@permission_required('projects', 'view')
def projects_list():
    """Projects list page"""
    company = get_active_company()
    is_collaborator = is_collaborator_in_company(company.id) if company else False
    can_create_projects_flag = can_create_projects(company.id) if company else False
    return render_template('modules/projects/projects_v2.html', company=company, is_collaborator=is_collaborator, can_create_projects=can_create_projects_flag)

@projects_bp.route('/projects/new')
@permission_required('projects', 'view')
def project_new():
    """New project form"""
    company = get_active_company()
    if company and not can_create_projects(company.id):
        abort(403, description='Acesso negado: usuário não pode criar projetos nesta empresa.')
    return render_template('modules/projects/project_form_v2.html', company=company)

@projects_bp.route('/projects/<int:project_id>/edit')
@permission_required('projects', 'edit')
def project_edit(project_id):
    """Edit project form"""
    project, company = _get_project_page_with_access(project_id)
    if company and not has_company_full_access(company.id):
        abort(403, description='Acesso negado: colaboradores não podem editar projetos.')
    return render_template('modules/projects/project_form_v2.html', project_id=project_id, company=company, project=project)

@projects_bp.route('/projects/<int:project_id>/manage')
@permission_required('projects', 'view')
def project_manage(project_id):
    """Project management (Kanban) page"""
    project, company = _get_project_page_with_access(project_id)
    is_collaborator = is_collaborator_in_company(company.id) if company else False
    can_edit_tasks = can_manage_project_tasks(company.id) if company else False
    
    # Define stages for Kanban
    stages = [
        {"slug": "inbox", "title": "Caixa de Entrada", "color": "#1e40af"},
        {"slug": "waiting", "title": "Aguardando", "color": "#b45309"},
        {"slug": "executing", "title": "Executando", "color": "#5b21b6"},
        {"slug": "pending", "title": "Pendências", "color": "#047857"},
        {"slug": "suspended", "title": "Suspensos", "color": "#94a3b8"},
        {"slug": "completed", "title": "Concluídos", "color": "#15803d"},
    ]
    
    return render_template('modules/projects/project_manage.html', 
                           project=project, 
                           company=company,
                           stages=stages,
                           is_collaborator=is_collaborator,
                           can_edit_tasks=can_edit_tasks)


@projects_bp.route('/api/projects/<int:project_id>/employees')
@permission_required('projects', 'view')
def project_employees(project_id):
    """Lista colaboradores ativos da empresa do projeto no escopo de acesso ao projeto."""
    from models import Employee

    project, company = _get_project_page_with_access(project_id)
    company_id = company.id if company else getattr(project, 'company_id', None)
    if not company_id:
        return jsonify({"success": False, "message": "Empresa do projeto não encontrada."}), 404

    employees = (
        Employee.query.filter_by(company_id=company_id, status='active')
        .order_by(Employee.name.asc())
        .all()
    )
    return jsonify({
        "success": True,
        "employees": [
            {"id": employee.id, "name": employee.name, "email": employee.email}
            for employee in employees
        ],
    })

@projects_bp.route('/projects/analysis')
@permission_required('projects', 'view')
def project_analysis():
    """Project analysis (All tasks Kanban) page"""
    company = get_active_company()
    is_collaborator = is_collaborator_in_company(company.id) if company else False
    can_edit_tasks = can_manage_project_tasks(company.id) if company else False
    
    # Define stages for Kanban
    stages = [
        {"slug": "inbox", "title": "Caixa de Entrada", "color": "#1e40af"},
        {"slug": "waiting", "title": "Aguardando", "color": "#b45309"},
        {"slug": "executing", "title": "Executando", "color": "#5b21b6"},
        {"slug": "pending", "title": "Pendências", "color": "#047857"},
        {"slug": "suspended", "title": "Suspensos", "color": "#94a3b8"},
        {"slug": "completed", "title": "Concluídos", "color": "#15803d"},
    ]
    
    return render_template('modules/projects/project_analysis.html', 
                           company=company,
                           stages=stages,
                           is_collaborator=is_collaborator,
                           can_edit_tasks=can_edit_tasks)


@projects_bp.route('/api/projects/<int:project_id>/summary-options')
@permission_required('projects', 'view')
def project_summary_options(project_id):
    from services.project_responsible_summary_service import build_summary_hint, build_summary_options, get_project_owner_user

    project, company = _get_project_page_with_access(project_id)
    if company and not has_company_full_access(company.id):
        return jsonify({'success': False, 'message': 'Acesso negado: colaboradores não podem disparar resumos.'}), 403

    target_user = get_project_owner_user(project)
    return jsonify({
        'success': True,
        'title': 'Resumo do Projeto',
        'options': build_summary_options(
            target_user,
            url_for('projects.project_summary_pdf', project_id=project.id),
            url_for('projects.send_project_owner_summary', project_id=project.id),
        ),
        'hint': build_summary_hint(target_user),
    })


@projects_bp.route('/api/projects/<int:project_id>/summary-pdf')
@projects_bp.route('/api/projects/<int:project_id>/summary.pdf')
@permission_required('projects', 'view')
def project_summary_pdf(project_id):
    from io import BytesIO
    from services.project_summary_pdf_service import generate_project_summary_pdf_bytes

    project, company = _get_project_page_with_access(project_id)
    if company and not has_company_full_access(company.id):
        abort(403, description='Acesso negado: colaboradores não podem gerar resumos.')

    pdf_bytes = generate_project_summary_pdf_bytes(project)
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'resumo-projeto-{project.code}.pdf',
    )


@projects_bp.route('/api/projects/<int:project_id>/summary', methods=['POST'])
@projects_bp.route('/api/projects/<int:project_id>/send-owner-summary', methods=['POST'])
@permission_required('projects', 'view')
def send_project_owner_summary(project_id):
    from services.project_responsible_summary_service import send_project_summary_to_owner

    project, company = _get_project_page_with_access(project_id)
    if company and not has_company_full_access(company.id):
        return jsonify({'success': False, 'message': 'Acesso negado: colaboradores não podem disparar resumos.'}), 403

    payload = request.get_json(silent=True) or {}
    preferred_channel = (payload.get('channel') or '').strip().lower() or None
    result = send_project_summary_to_owner(project, preferred_channel=preferred_channel)
    if not result.get('success'):
        return jsonify({'success': False, 'message': result.get('error') or 'Falha ao enviar resumo', 'result': result}), 400

    channel_label = {'email': 'E-mail', 'whatsapp': 'WhatsApp'}.get(result.get('delivery_channel'), result.get('delivery_channel'))
    return jsonify({
        'success': True,
        'message': f"Resumo do projeto enviado com sucesso via {channel_label}",
        'result': result,
    })
