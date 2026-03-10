from flask import Blueprint, render_template, session, jsonify, abort
from models import Company
from flask_login import current_user

from utils.permissions import get_default_company_id, permission_required, has_company_full_access, is_collaborator_in_company

projects_bp = Blueprint('projects', __name__)

def _get_project_page_with_access(project_id):
    from models import Project
    from api.resources.project import apply_project_employee_filter

    company = get_active_company()
    company_id = company.id if company else None
    if not company_id:
        return None, None

    query = Project.query.filter_by(id=project_id, company_id=company_id)
    query = apply_project_employee_filter(query, company_id)
    return query.first_or_404(), company

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
    return render_template('modules/projects/projects_v2.html', company=company, is_collaborator=is_collaborator)

@projects_bp.route('/projects/new')
@permission_required('projects', 'create')
def project_new():
    """New project form"""
    company = get_active_company()
    if company and not has_company_full_access(company.id):
        abort(403, description='Acesso negado: colaboradores não podem criar projetos.')
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
                           is_collaborator=is_collaborator)

@projects_bp.route('/projects/analysis')
@permission_required('projects', 'view')
def project_analysis():
    """Project analysis (All tasks Kanban) page"""
    company = get_active_company()
    is_collaborator = is_collaborator_in_company(company.id) if company else False
    
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
                           is_collaborator=is_collaborator)


@projects_bp.route('/api/projects/<int:project_id>/send-owner-summary', methods=['POST'])
@permission_required('projects', 'view')
def send_project_owner_summary(project_id):
    from services.project_responsible_summary_service import send_project_summary_to_owner

    project, company = _get_project_page_with_access(project_id)
    if company and not has_company_full_access(company.id):
        return jsonify({'success': False, 'message': 'Acesso negado: colaboradores não podem disparar resumos.'}), 403
    result = send_project_summary_to_owner(project)
    if not result.get('success'):
        return jsonify({'success': False, 'message': result.get('error') or 'Falha ao enviar resumo', 'result': result}), 400

    return jsonify({
        'success': True,
        'message': f"Resumo do projeto enviado com sucesso via {result.get('delivery_channel')}",
        'result': result,
    })
