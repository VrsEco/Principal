from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from models import Company, Indicator, Process, Project, OKRGlobal, User, OKRArea, IndicatorData, IndicatorGoal, Employee, Meeting, db
from sqlalchemy import func, or_
from datetime import datetime
from utils.permissions import has_company_full_access, get_default_company_id

main_bp = Blueprint('main', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'


def _active_employee_filter():
    return or_(Employee.status == 'active', Employee.status.is_(None))


def _resolve_active_company():
    company_id = request.args.get('company_id', type=int) or session.get('active_company_id')

    if not company_id and current_user.is_authenticated:
        employee = (
            Employee.query
            .filter(Employee.user_id == current_user.id, _active_employee_filter())
            .order_by(Employee.company_id.asc())
            .first()
        )
        if employee and employee.company_id:
            company_id = employee.company_id
        else:
            company_id = get_default_company_id()

    company = Company.query.get(company_id) if company_id else None
    if company:
        session['active_company_id'] = company.id
    return company

@main_bp.route('/')
def index():
    """Redirect to login or dashboard based on auth status"""
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('my_work.my_work'))
    return redirect(url_for('auth.login'))

@main_bp.route('/styleguide')
def styleguide():
    """Styleguide page"""
    return render_template('styleguide.html')


@main_bp.route('/operations')
@login_required
def operations_hub():
    """Central unificada de operações inteligentes do APP32."""
    active_company = _resolve_active_company()
    modules = [
        {
            "key": "financial",
            "label": "Gestão Financeira",
            "icon": "currency",
            "description": "Importações, lançamentos, classificação assistida, automações e revisão operacional.",
            "groups": [
                {
                    "label": "Importações",
                    "items": [
                        {
                            "title": "Prestação de contas",
                            "description": "Importar documento, sugerir lançamentos e revisar vínculos antes da confirmação.",
                            "href": "/financial/accountability",
                            "badge": "Piloto prioritário",
                            "mode": "Assistida",
                        },
                        {
                            "title": "Entradas / Integrações IA",
                            "description": "Acompanhar documentos, lotes e registros trazidos por integrações e importações.",
                            "href": "/financial/ingestions",
                            "mode": "Automática",
                        },
                    ],
                },
                {
                    "label": "Configurações operacionais",
                    "items": [
                        {
                            "title": "Cadastros-base",
                            "description": "Contas bancárias, plano de contas, centros de resultado e favorecidos.",
                            "href": "/financial/catalogs",
                            "mode": "Manual",
                        },
                        {
                            "title": "Projetos / Processos habilitados",
                            "description": "Definir os domínios que podem ser vinculados às operações financeiras.",
                            "href": "/financial/domain-enablements",
                            "mode": "Manual",
                        },
                    ],
                },
                {
                    "label": "Execução assistida",
                    "items": [
                        {
                            "title": "Classificação IA",
                            "description": "Fila, regras e memórias da classificação assistida do financeiro.",
                            "href": "/financial/classification-queue",
                            "mode": "Assistida",
                        },
                        {
                            "title": "Automação IA",
                            "description": "Regras automatizadas e auditoria das ações executadas no módulo.",
                            "href": "/financial/automation-rules",
                            "mode": "Automática",
                        },
                    ],
                },
            ],
        },
        {
            "key": "projects",
            "label": "Projetos",
            "icon": "folder",
            "description": "Criação, execução e acompanhamento de projetos e atividades.",
            "groups": [
                {
                    "label": "Operações",
                    "items": [
                        {
                            "title": "Projetos",
                            "description": "Gerenciar cadastro, andamento e contexto dos projetos em execução.",
                            "href": "/projects",
                            "mode": "Manual",
                        },
                        {
                            "title": "Atividades de projeto",
                            "description": "Criar e acompanhar tarefas, responsáveis e prazos.",
                            "href": "/projects",
                            "mode": "Assistida",
                        },
                    ],
                },
            ],
        },
        {
            "key": "processes",
            "label": "Processos",
            "icon": "workflow",
            "description": "Mapeamento, execução e melhoria contínua dos processos.",
            "groups": [
                {
                    "label": "Operações",
                    "items": [
                        {
                            "title": "Mapa de processos",
                            "description": "Visualizar a estrutura e manter o desenho operacional dos processos.",
                            "href": "/processes/map",
                            "mode": "Manual",
                        },
                        {
                            "title": "Instâncias de processo",
                            "description": "Acompanhar etapas, prazos e execução operacional do dia a dia.",
                            "href": "/processes/instances",
                            "mode": "Assistida",
                        },
                    ],
                },
            ],
        },
        {
            "key": "meetings",
            "label": "Reuniões",
            "icon": "meeting",
            "description": "Agendamento, condução, ata e follow-up das reuniões.",
            "groups": [
                {
                    "label": "Execução",
                    "items": [
                        {
                            "title": "Gerenciar reuniões",
                            "description": "Agendar, iniciar, registrar decisões, encerrar e enviar atas.",
                            "href": "/meetings/manage-v2",
                            "mode": "Assistida",
                        },
                    ],
                },
            ],
        },
        {
            "key": "journey",
            "label": "Jornada",
            "icon": "calendar",
            "description": "Agenda operacional, regras, blocos e redistribuição de carga.",
            "groups": [
                {
                    "label": "Operações",
                    "items": [
                        {
                            "title": "Meu Trabalho",
                            "description": "Visualizar agenda, prioridades, rotinas, tarefas e jornada operacional.",
                            "href": "/my-work",
                            "mode": "Assistida",
                        },
                    ],
                },
            ],
        },
        {
            "key": "technical",
            "label": "Administração técnica",
            "icon": "settings",
            "description": "Catálogo técnico, integrações, Sapiens, MCP e observabilidade do sistema.",
            "groups": [
                {
                    "label": "Backoffice técnico",
                    "items": [
                        {
                            "title": "Sapiens",
                            "description": "Acesso direto ao agente conversacional e seus fluxos operacionais atuais.",
                            "href": "/sapiens",
                            "mode": "Técnico",
                        },
                        {
                            "title": "Integrações",
                            "description": "Central atual de integrações e pontos de conectividade do APP32.",
                            "href": "/integrations",
                            "mode": "Técnico",
                        },
                        {
                            "title": "Configurações de IA",
                            "description": "Configurações, parâmetros e ajustes operacionais relacionados à inteligência.",
                            "href": "/configurations/ai",
                            "mode": "Técnico",
                        },
                    ],
                },
            ],
        },
    ]
    return render_template(
        'modules/operations/hub.html',
        active_company=active_company,
        modules=modules,
    )

@main_bp.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Returns filtered analytics and counts for the dashboard cards"""
    from flask import session
    company_id = request.args.get('company_id', type=int)
    
    # Use session company if none provided
    if not company_id:
        company_id = session.get('active_company_id')
        
    project_id = request.args.get('project_id', type=int)
    process_id = request.args.get('process_id', type=int)
    responsible = request.args.get('responsible')
    executor_id = request.args.get('executor_id', type=int)
    
    # Date filters (Simple strings for now, converted if needed)
    d_reg_s = request.args.get('d_reg_s')
    d_reg_e = request.args.get('d_reg_e')
    d_due_s = request.args.get('d_due_s')
    d_due_e = request.args.get('d_due_e')
    d_done_s = request.args.get('d_done_s')
    d_done_e = request.args.get('d_done_e')

    def apply_base_filters(query, model):
        if company_id and hasattr(model, 'company_id'):
            query = query.filter(model.company_id == company_id)
        
        # Apply Project and Process filters if the model supports them
        if project_id and hasattr(model, 'project_id'):
            query = query.filter(model.project_id == project_id)
        if process_id and hasattr(model, 'process_id'):
            query = query.filter(model.process_id == process_id)

        if responsible:
            if hasattr(model, 'owner'):
                query = query.filter(model.owner.ilike(f"%{responsible}%"))
            elif hasattr(model, 'responsible'):
                query = query.filter(model.responsible.ilike(f"%{responsible}%"))
            elif hasattr(model, 'who'): # for ProjectTask
                query = query.filter(model.who.ilike(f"%{responsible}%"))
        
        # Registration date filters
        if d_reg_s and hasattr(model, 'created_at'):
            query = query.filter(model.created_at >= d_reg_s)
        if d_reg_e and hasattr(model, 'created_at'):
            query = query.filter(model.created_at <= d_reg_e)
            
        # Due date filters
        if d_due_s:
            if hasattr(model, 'deadline'):
                query = query.filter(model.deadline >= d_due_s)
            elif hasattr(model, 'due_date'):
                query = query.filter(model.due_date >= d_due_s)
        if d_due_e:
            if hasattr(model, 'deadline'):
                query = query.filter(model.deadline <= d_due_e)
            elif hasattr(model, 'due_date'):
                query = query.filter(model.due_date <= d_due_e)
                
        return query

    # 1. Counts with Filters
    q_companies = Company.query.filter_by(is_active=True)
    if d_reg_s: q_companies = q_companies.filter(Company.created_at >= d_reg_s)
    if d_reg_e: q_companies = q_companies.filter(Company.created_at <= d_reg_e)
    
    q_indicators = Indicator.query
    if company_id: q_indicators = q_indicators.filter(Indicator.company_id == company_id)
    # project_id and process_id are now handled by apply_base_filters
    q_indicators = apply_base_filters(q_indicators, Indicator)
    
    q_processes = Process.query
    if company_id: q_processes = q_processes.filter(Process.company_id == company_id)
    if process_id: q_processes = q_processes.filter(Process.id == process_id)
    q_processes = apply_base_filters(q_processes, Process)
    
    q_projects = Project.query
    if company_id:
        q_projects = q_projects.filter(Project.company_id == company_id)
    if project_id:
        q_projects = q_projects.filter(Project.id == project_id)
    q_projects = apply_base_filters(q_projects, Project)
    
    q_okrs_g = apply_base_filters(OKRGlobal.query, OKRGlobal)
    q_okrs_a = apply_base_filters(OKRArea.query, OKRArea)
    
    # Task Counts
    from models import ProjectTask, Project, ProcessInstance
    
    q_proj_tasks = ProjectTask.query
    q_proc_inst = ProcessInstance.query
    
    import sqlalchemy as sa
    if project_id:
        q_proj_tasks = q_proj_tasks.filter(ProjectTask.project_id == project_id)
        q_proc_inst = q_proc_inst.filter(sa.false()) # Project focus hides processes
    elif process_id:
        q_proc_inst = q_proc_inst.filter(ProcessInstance.process_id == process_id)
        q_proj_tasks = q_proj_tasks.filter(sa.false()) # Process focus hides project tasks
    elif company_id:
        q_proj_tasks = q_proj_tasks.join(Project).filter(Project.company_id == company_id)
        q_proc_inst = q_proc_inst.filter(ProcessInstance.company_id == company_id)
    
    q_proj_tasks = apply_base_filters(q_proj_tasks, ProjectTask)
    q_proc_inst = apply_base_filters(q_proc_inst, ProcessInstance)
    
    q_meetings = Meeting.query
    if company_id: q_meetings = q_meetings.filter(Meeting.company_id == company_id)
    q_meetings = apply_base_filters(q_meetings, Meeting)

    pending_tasks = q_proj_tasks.filter(ProjectTask.status != 'completed').count() + \
                   q_proc_inst.filter(ProcessInstance.status != 'completed').count()
                   
    today = datetime.utcnow().date()
    overdue_tasks = q_proj_tasks.filter(ProjectTask.status != 'completed', ProjectTask.due_date < today).count() + \
                    q_proc_inst.filter(ProcessInstance.status != 'completed', ProcessInstance.due_date < today).count()

    counts = {
        "companies": q_companies.count(),
        "indicators": q_indicators.count(),
        "processes": q_processes.count(),
        "projects": q_projects.count(),
        "okrs": q_okrs_g.count() + q_okrs_a.count(),
        "meetings": q_meetings.count(),
        "users": User.query.count(),
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks
    }

    # 2. Performance Logic (Filtered)
    indicator_perf = 0
    kpis = q_indicators.all()
    if kpis:
        total_p = 0
        count_p = 0
        for k in kpis:
            goal = IndicatorGoal.query.filter_by(indicator_id=k.id, status='active')
            if d_due_s: goal = goal.filter(IndicatorGoal.goal_date >= d_due_s)
            if d_due_e: goal = goal.filter(IndicatorGoal.goal_date <= d_due_e)
            goal = goal.order_by(IndicatorGoal.goal_date.desc()).first()
            
            if goal and goal.goal_value > 0:
                last_data = IndicatorData.query.filter_by(goal_id=goal.id).order_by(IndicatorData.record_date.desc()).first()
                if last_data:
                    achievement = (float(last_data.value) / float(goal.goal_value)) * 100
                    if k.polarity == 'negative':
                        achievement = (float(goal.goal_value) / float(last_data.value)) * 100 if last_data.value > 0 else 100
                    total_p += min(achievement, 150)
                    count_p += 1
        indicator_perf = round(total_p / count_p) if count_p > 0 else 0

    project_avg_progress = q_projects.with_entities(func.avg(Project.progress)).scalar()
    project_avg_progress = float(project_avg_progress) if project_avg_progress is not None else 0.0
    
    # OKR Progress Calculation (compatível com esquemas diferentes)
    def _okr_progress_value(okr_obj) -> float:
        # Alguns bancos/modelos não possuem `progress`
        val = getattr(okr_obj, "progress", None)
        if val is None:
            val = getattr(okr_obj, "progress_overall", None)
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    okrs = q_okrs_g.all() + q_okrs_a.all()
    if okrs:
        okr_progress = round(sum(_okr_progress_value(o) for o in okrs) / len(okrs))
    else:
        okr_progress = 0
        
    global_score = round((float(okr_progress) * 0.4) + (float(indicator_perf) * 0.4) + (float(project_avg_progress) * 0.2))

    return jsonify({
        "counts": counts,
        "performance": {
            "global_score": global_score,
            "kpis_avg": indicator_perf,
            "projects_avg": round(project_avg_progress),
            "okr_avg": okr_progress
        }
    })

@main_bp.route('/api/dashboard/filter-options')
@login_required
def dashboard_filter_options():
    try:
        from flask_login import current_user
        company_id = request.args.get('company_id', type=int) or session.get('active_company_id')

        if company_id and has_company_full_access(company_id):
            if company_id:
                companies = Company.query.filter_by(id=company_id, is_active=True).all()
                employees = (
                    Employee.query
                    .filter(Employee.company_id == company_id, _active_employee_filter())
                    .order_by(Employee.name)
                    .all()
                )
                projects = Project.query.filter_by(company_id=company_id).all()
                processes = Process.query.filter_by(company_id=company_id).all()
            else:
                companies = Company.query.filter_by(is_active=True).all()
                employees = (
                    Employee.query
                    .filter(_active_employee_filter())
                    .order_by(Employee.name)
                    .all()
                )
                projects = Project.query.all()
                processes = Process.query.all()
        else:
            employee_records = (
                Employee.query
                .filter(Employee.user_id == current_user.id, _active_employee_filter())
                .all()
            )
            company_ids = [e.company_id for e in employee_records]
            
            if company_id:
                if company_id not in company_ids:
                    return jsonify({"success": False, "error": "Access denied"}), 403
                company_ids = [company_id]
            
            companies = Company.query.filter(Company.id.in_(company_ids), Company.is_active==True).all()
            employees = (
                Employee.query
                .filter(Employee.company_id.in_(company_ids), _active_employee_filter())
                .order_by(Employee.name)
                .all()
            )
            projects = Project.query.filter(Project.company_id.in_(company_ids)).all()
            processes = Process.query.filter(Process.company_id.in_(company_ids)).all()
        
        return jsonify({
            "companies": [{"id": c.id, "name": c.name} for c in companies],
            "employees": [{"id": e.id, "name": e.name} for e in employees],
            "projects": [{"id": p.id, "name": p.name} for p in projects],
            "processes": [{"id": p.id, "name": p.name, "code": p.code} for p in processes]
        })
    except Exception as e:
        current_app.logger.exception("Erro ao montar opções de filtro do dashboard")
        return jsonify({"error": PUBLIC_ERROR_MESSAGE}), 500


@main_bp.route('/main')
@login_required
def main_notes():
    """Annotations/Notes page (Ecosystem)"""
    return render_template('notation.html')

@main_bp.route('/efficiency-analysis')
@login_required
def efficiency_analysis():
    """Efficiency Analysis Page"""
    from flask import session
    company_id = session.get('active_company_id')
    return render_template('efficiency_analysis.html', company_id=company_id)

@main_bp.errorhandler(404)
def page_404(e=None):
    """404 error page"""
    return render_template('404.html'), 404
