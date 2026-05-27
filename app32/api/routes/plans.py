from flask import Blueprint, render_template, session, redirect, url_for, request, abort
from flask_login import login_required, current_user
from services.plan_service import PlanService
from api.routes.projects import get_active_company
from utils.permissions import has_company_full_access

plans_bp = Blueprint('plans', __name__, url_prefix='/plans')



def _ensure_plans_access(company):
    if not company:
        return
    if not has_company_full_access(company.id):
        abort(403, description='Acesso negado: Colaboradores não podem acessar planos.')


@plans_bp.route('/')
@login_required
def plans_list():
    """List all plans for the active company."""
    company = get_active_company()
    _ensure_plans_access(company)
    if not company:
        return redirect(url_for('auth.portal'))

    plans = PlanService.list_plans(company.id)
    return render_template('modules/plans/plans_list.html', company=company, plans=plans)

@plans_bp.route('/<int:plan_id>/growth')
@login_required
def growth_dashboard(plan_id):
    """Growth planning dashboard."""
    company = get_active_company()
    company_id = company.id if company else None
    _ensure_plans_access(company)

    data = PlanService.get_plan_dashboard_data(plan_id, company_id)
    if not data or data['plan']['mode'] != 'growth':
        return redirect(url_for('plans.plans_list'))
        
    return render_template('modules/plans/growth_dashboard.html', 
                           plan=data['plan'], 
                           company=company,
                           sections=data['sections'],
                           active_section='dashboard',
                           drivers_count=data['stats']['drivers_count'],
                           okrs_count=data['stats']['okrs_count'],
                           completed_sections=data['stats']['completed_sections'],
                           total_completable=data['stats']['total_completable'])

@plans_bp.route('/<int:plan_id>/growth/<section>')
@login_required
def growth_section(plan_id, section):
    """Render a specific section of the growth plan."""
    company = get_active_company()
    _ensure_plans_access(company)
    plan = PlanService.get_plan(plan_id, company.id if company else None)
    
    if not plan or plan.mode != 'growth':
        return redirect(url_for('plans.plans_list'))
    
    # Map section keys to template names
    template_map = {
        'dashboard': 'modules/plans/growth_dashboard.html',
        'participants': 'modules/plans/growth_participants.html',
        'drivers': 'modules/plans/growth_drivers.html',
        'okrs_global': 'modules/plans/growth_okrs_global.html',
        'okrs_area': 'modules/plans/growth_okrs_area.html',
        'projects': 'modules/plans/growth_projects.html',
        'final_report': 'modules/plans/growth_report.html',
    }
    
    template = template_map.get(section)
    if not template:
        return redirect(url_for('plans.growth_dashboard', plan_id=plan_id))
        
    # Get extra data based on section
    extra_data = {}
    if section == 'drivers':
        from models import PlanDriver
        extra_data['drivers'] = PlanDriver.query.filter_by(plan_id=plan_id).all()
    elif section == 'okrs_global':
        from models import OKRGlobal, PlanParticipant, PlanDriver
        extra_data['okrs'] = OKRGlobal.query.filter_by(plan_id=plan_id, company_id=company.id).all()
        extra_data['participants'] = PlanParticipant.query.filter_by(plan_id=plan_id).all()
        extra_data['drivers'] = PlanDriver.query.filter_by(plan_id=plan_id).all()
    elif section == 'okrs_area':
        from models import OKRArea, PlanParticipant, OKRGlobal
        extra_data['okrs_area'] = OKRArea.query.filter_by(plan_id=plan_id, company_id=company.id).all()
        extra_data['participants'] = PlanParticipant.query.filter_by(plan_id=plan_id).all()
        extra_data['okrs_global'] = OKRGlobal.query.filter_by(plan_id=plan_id, company_id=company.id).all()
    elif section == 'projects':
        from models import Project, PlanParticipant, OKRArea, Portfolio, Employee
        extra_data['projects'] = Project.query.filter_by(plan_id=plan_id, company_id=company.id).all()
        extra_data['participants'] = PlanParticipant.query.filter_by(plan_id=plan_id).all()
        extra_data['okrs_area'] = OKRArea.query.filter_by(plan_id=plan_id, company_id=company.id).all()
        extra_data['portfolios'] = Portfolio.query.filter_by(company_id=company.id).all()
        extra_data['employees'] = Employee.query.filter_by(company_id=company.id, status='active').order_by(Employee.name).all()
    elif section == 'participants':
        from models import Employee, PlanParticipant
        # Fetch all active employees that are NOT already added (or just all and filter in frontend)
        # For simplicity, passing all active employees
        extra_data['employees'] = Employee.query.filter_by(company_id=company.id, status='active').order_by(Employee.name).all()
        extra_data['participants'] = PlanParticipant.query.filter_by(plan_id=plan_id).all()
        
    # Common sections for sidebar
    sections = PlanService.get_sections_config('growth')
    
    return render_template(template, 
                           plan=plan, 
                           company=company, 
                           sections=sections,
                           active_section=section,
                           **extra_data)

@plans_bp.route('/<int:plan_id>/implantation')
@login_required
def implantation_dashboard(plan_id):
    """Implantation planning dashboard."""
    company = get_active_company()
    company_id = company.id if company else None
    _ensure_plans_access(company)

    data = PlanService.get_plan_dashboard_data(plan_id, company_id)
    if not data or data['plan']['mode'] != 'implantation':
        return redirect(url_for('plans.plans_list'))
        
    return render_template('modules/plans/implantation_dashboard.html', 
                           plan=data['plan'], 
                           company=company,
                           sections=data['sections'],
                           active_section='dashboard',
                           completed_sections=data['stats']['completed_sections'],
                           total_completable=data['stats']['total_completable'],
                           total_investment=data['finance']['total_investment'],
                           payback=data['finance']['payback'],
                           participants_count=data['stats']['participants_count'])


@plans_bp.route('/<int:plan_id>/implantation/<section>')
@login_required
def implantation_section(plan_id, section):
    """Render a specific section of the implantation plan."""
    company = get_active_company()
    _ensure_plans_access(company)
    plan = PlanService.get_plan(plan_id, company.id if company else None)
    
    if not plan or plan.mode != 'implantation':
        return redirect(url_for('plans.plans_list'))
    
    template_map = {
        'dashboard': 'modules/plans/implantation_dashboard.html',
        'participants': 'modules/plans/growth_participants.html',
        'alignment': 'modules/plans/implantation_alignment.html',
        'model': 'modules/plans/implantation_model.html',
        'execution': 'modules/plans/implantation_execution.html',
        'finance': 'modules/plans/implantation_finance.html',
        'projects': 'modules/plans/growth_projects.html',
        'final_report': 'modules/plans/implantation_report.html',
    }
    
    template = template_map.get(section)
    if not template:
        return redirect(url_for('plans.implantation_dashboard', plan_id=plan_id))
        
    # Get content from PlanImplantationData
    section_data = PlanService.get_implantation_data(plan_id, company.id, section)
    section_content = section_data.content if section_data else {}
        
    sections = PlanService.get_sections_config('implantation')
    
    # Get status for each section
    from models import PlanSectionStatus
    statuses = {s.section_key: s.status for s in plan.section_statuses.all()}
    for s in sections:
        s['status'] = statuses.get(s['key'], 'pending')

    # Get extra data based on section
    extra_data = {}
    if section == 'participants':
        from models import Employee, PlanParticipant
        extra_data['employees'] = Employee.query.filter_by(company_id=company.id, status='active').order_by(Employee.name).all()
        extra_data['participants'] = PlanParticipant.query.filter_by(plan_id=plan_id).all()
    elif section == 'projects':
        from models import Project, PlanParticipant, OKRArea, Portfolio, Employee
        extra_data['projects'] = Project.query.filter_by(plan_id=plan_id, company_id=company.id).all()
        extra_data['participants'] = PlanParticipant.query.filter_by(plan_id=plan_id).all()
        extra_data['okrs_area'] = OKRArea.query.filter_by(plan_id=plan_id, company_id=company.id).all()
        extra_data['portfolios'] = Portfolio.query.filter_by(company_id=company.id).all()
        extra_data['employees'] = Employee.query.filter_by(company_id=company.id, status='active').order_by(Employee.name).all()
        
    # Extra data for Finance
    if section == 'finance':
        extra_data['consolidated'] = PlanService.get_consolidated_finance(plan_id, company.id)
        
        # Safe normalization for template display
        # 1. Sources (handle legacy list)
        sources = section_content.get('sources', {})
        if isinstance(sources, list):
            section_content['sources'] = { (s.get('description') or s.get('category') or f"Fonte {i}"): s.get('amount', 0) for i, s in enumerate(sources) if isinstance(s, dict) }
        elif not isinstance(sources, dict):
            section_content['sources'] = {}

        # 2. Working Capital
        if 'working_capital' not in section_content:
            section_content['working_capital'] = {
                'cash_reserve': 0, 'receivables_days': 30, 'inventory_days': 30, 'payable_days': 30,
                'cash_items': [], 'receivables_items': [], 'inventory_items': []
            }
        else:
            # Ensure the new lists exist for existing data
            wc = section_content['working_capital']
            for list_key in ['cash_items', 'receivables_items', 'inventory_items']:
                if list_key not in wc:
                    wc[list_key] = []
        
        # 3. Analysis Params
        if 'analysis_params' not in section_content:
            section_content['analysis_params'] = {
                'period_months': 60, 'opportunity_cost_annual': 12.0
            }
            
        # 4. Profit Distribution
        if 'profit_distribution' not in section_content:
            section_content['profit_distribution'] = []

        # 5. Taxes
        if 'taxes' not in section_content:
            section_content['taxes'] = []

        # 6. Source Dates
        if 'source_dates' not in section_content:
            section_content['source_dates'] = {}

    if section == 'final_report':
        extra_data['report_context'] = PlanService.get_implantation_report_context(plan_id, company.id)

    # Pass values specifically to avoid dict method collision
    alignment_values = section_content.get('values', [])

    return render_template(template, 
                           plan=plan, 
                           company=company, 
                           sections=sections,
                           active_section=section,
                           section_content=section_content,
                           alignment_values=alignment_values,
                           **extra_data)

@plans_bp.route('/<int:plan_id>/sections/<section_key>/complete', methods=['POST'])
@login_required
def complete_section(plan_id, section_key):
    """Mark a section as completed."""
    company = get_active_company()
    _ensure_plans_access(company)
    plan = PlanService.get_plan(plan_id, company.id if company else None)
    
    if not plan:
        return {"error": "Plan not found"}, 404
        
    PlanService.update_section_status(plan_id, section_key, 'completed', company_id=company.id if company else None)
    
    return {"status": "success", "message": "Section marked as completed"}

@plans_bp.route('/<int:plan_id>/update', methods=['POST'])
@login_required
def update_plan(plan_id):
    """Update plan title and description."""
    company = get_active_company()
    _ensure_plans_access(company)
    if not company:
        return {"error": "Empresa não encontrada"}, 404
        
    data = request.get_json()
    plan = PlanService.update_plan(plan_id, company.id, data)
    
    if not plan:
        return {"error": "Plano não encontrado"}, 404
        
    return {"status": "success", "message": "Plano atualizado com sucesso"}

@plans_bp.route('/<int:plan_id>/delete', methods=['POST'])
@login_required
def delete_plan(plan_id):
    """Delete a plan."""
    company = get_active_company()
    if not company:
        return {"error": "Empresa não encontrada"}, 404
        
    success = PlanService.delete_plan(plan_id, company.id)
    
    if not success:
        return {"error": "Erro ao excluir o plano ou plano não encontrado"}, 400
        
    return {"status": "success", "message": "Plano excluído com sucesso"}
