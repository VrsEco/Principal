from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_restful import Api
import os
from sqlalchemy import inspect, or_, text

from models import db
from schemas import ma


def _backfill_user_channel_contacts():
    """Move legacy contacts from employees to users when user fields are empty."""
    from models.employee import Employee
    from models.user import User

    employees = (
        Employee.query.filter(Employee.user_id.isnot(None))
        .filter(or_(Employee.whatsapp.isnot(None), Employee.telegram.isnot(None)))
        .all()
    )
    if not employees:
        return {"users_updated": 0, "whatsapp_filled": 0, "telegram_filled": 0}

    user_ids = sorted({emp.user_id for emp in employees if emp.user_id})
    users_by_id = {user.id: user for user in User.query.filter(User.id.in_(user_ids)).all()}

    users_updated = 0
    whatsapp_filled = 0
    telegram_filled = 0

    for emp in employees:
        user = users_by_id.get(emp.user_id)
        if not user:
            continue

        changed = False
        emp_whatsapp = (emp.whatsapp or "").strip()
        emp_telegram = (emp.telegram or "").strip()
        user_whatsapp = (user.whatsapp or "").strip()
        user_telegram = (user.telegram or "").strip()

        if emp_whatsapp and not user_whatsapp:
            user.whatsapp = emp_whatsapp
            whatsapp_filled += 1
            changed = True

        if emp_telegram and not user_telegram:
            user.telegram = emp_telegram
            telegram_filled += 1
            changed = True

        if changed:
            users_updated += 1

    if users_updated:
        db.session.commit()

    return {
        "users_updated": users_updated,
        "whatsapp_filled": whatsapp_filled,
        "telegram_filled": telegram_filled,
    }


def create_app(config_name=None):
    app = Flask(__name__)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    print("DEBUG: Registering Jinja filters...")

    @app.template_filter('format_date_br')
    def format_date_br_filter(value, include_time=False):
        from utils.jinja_filters import format_date_br
        return format_date_br(value, include_time)

    CORS(app)

    # Configuration
    from config import config as app_configs
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV') or os.environ.get('FLASK_CONFIG', 'default')
        
    # Garante fallback seguro
    if config_name not in app_configs:
        config_name = 'default'
    
    app.config.from_object(app_configs[config_name])
    
    # Ensure Upload Dirs (keep hardcoded if not in config)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Extensions
    from flask_migrate import Migrate
    migrate = Migrate()
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)

    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.query.get(int(user_id))

    print("DEBUG: Registering API resources...")
    # RESTful API
    api = Api(app)
    register_api_resources(api)
    print("DEBUG: API resources registered.")

    print("DEBUG: Registering blueprints...")
    # Blueprints
    register_blueprints(app)
    print("DEBUG: Blueprints registered.")

    # Ensure Upload Dirs
    for folder in ['flows', 'pop']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)

    print("DEBUG: Checking DB connection and creating tables...")
    with app.app_context():
        try:
            db.create_all()
            inspector = inspect(db.engine)
            table_names = set(inspector.get_table_names())
            if "users" in table_names:
                user_columns = {col["name"] for col in inspector.get_columns("users")}
                with db.engine.begin() as conn:
                    if "instagram" not in user_columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN instagram VARCHAR(100)"))
                        print("DEBUG: users.instagram column added successfully.")
                    if "summary_delivery_channels" not in user_columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN summary_delivery_channels VARCHAR(100) NOT NULL DEFAULT 'telegram'"))
                        print("DEBUG: users.summary_delivery_channels column added successfully.")
            if {"users", "employees"}.issubset(table_names):
                stats = _backfill_user_channel_contacts()
                print(
                    "DEBUG: users contact backfill completed "
                    f"(users={stats['users_updated']}, "
                    f"whatsapp={stats['whatsapp_filled']}, "
                    f"telegram={stats['telegram_filled']})."
                )
            print("DEBUG: DB tables verified/created successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Error in db.create_all(): {e}")

    @app.context_processor
    def inject_permissions():
        from flask import session
        from flask_login import current_user
        from utils.permissions import (
            get_access_profile,
            get_default_company_id,
            has_company_full_access,
            has_permission,
            is_administrator,
            is_client_user,
            is_collaborator_in_company,
            is_platform_admin,
        )

        def _resolve_company_id(company_id=None):
            return company_id or session.get('active_company_id') or get_default_company_id()

        def check_perm(resource, action, company_id=None):
            if not current_user.is_authenticated:
                return False

            cid = _resolve_company_id(company_id)
            if cid:
                return has_permission(cid, resource, action)
            return has_permission(None, resource, action)

        def current_access_profile(company_id=None):
            return get_access_profile(_resolve_company_id(company_id))

        return dict(
            has_permission=check_perm,
            current_access_profile=current_access_profile,
            is_platform_admin=is_platform_admin,
            is_client_user=is_client_user,
            is_administrator=lambda company_id=None: is_administrator(_resolve_company_id(company_id)),
            has_company_full_access=lambda company_id=None: has_company_full_access(_resolve_company_id(company_id)),
            is_collaborator_in_company=lambda company_id=None: is_collaborator_in_company(_resolve_company_id(company_id)),
        )

    @app.context_processor
    def inject_active_company():
        from flask import session
        from models.company import Company
        company_id = session.get('active_company_id')
        if company_id:
            # Simple caching to avoid multiple queries in the same request if possible
            # though Flask-SQLAlchemy might handle this
            company = Company.query.get(company_id)
            return dict(active_company=company)
        return dict(active_company=None)

    @app.context_processor
    def inject_visual_theme_tokens():
        from src.core.theme_tokens import get_web_theme_tokens

        return dict(vs_theme=get_web_theme_tokens())

    @app.before_request
    def enforce_login():
        from flask import request, redirect, url_for, jsonify, session
        from flask_login import current_user
        import os
        from datetime import datetime
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(base_dir, 'request_debug.log')
        
        # Public endpoints that don't require authentication
        public_endpoints = ['auth.login', 'static', 'dev.seed_demo', 'dev.debug_routes', 'telegram.telegram_webhook']
        
        try:
            with open(log_path, 'a') as f:
                f.write(f"[{datetime.now()}] {request.method} {request.path}\n")
                f.write(f"  Auth: {current_user.is_authenticated}, Active Company: {session.get('active_company_id')}\n")
        except:
            pass

        # 1. Check if user is authenticated
        if not current_user.is_authenticated:
            # Além dos public_endpoints, libere também prefixos abertos (ex: webhooks externos)
            if request.endpoint and request.endpoint not in public_endpoints and not request.path.startswith('/webhook/'):
                # If it's an API call, return 401
                if '/api/' in request.path:
                    return jsonify({"error": "Authentication required"}), 401
                # Otherwise redirect to login
                return redirect(url_for('auth.login'))
        
        # 2. If authenticated, ensure company is selected
        else:
            # Endpoints allowed without selecting a company
            allowed_post_login = [
                'auth.portal',
                'auth.profile',
                'auth.change_password',
                'auth.logout',
                'static',
                'dev.seed_demo',
                'dev.debug_routes',
                'integrations.integrations_page',
            ]
            
            active_company_id = session.get('active_company_id')
            # Normalize 'null' and 'undefined' strings that might come from frontend/session issues
            if str(active_company_id).lower() in ['null', 'undefined', 'none', '']:
                active_company_id = None
            
            if not active_company_id:
                if request.endpoint and request.endpoint not in allowed_post_login:
                    # Redirect to selection page for UI routes
                    if '/api/' not in request.path:
                        try:
                            with open(log_path, 'a') as f:
                                f.write(f"  No active company, redirecting UI to portal\n")
                        except: pass
                        return redirect(url_for('auth.portal'))
    
    print("DEBUG: Starting Engineering Service worker...")
    from services.engineering_service import engineering_service
    engineering_service.start_worker(app)
    print("DEBUG: Engineering Service worker started.")

    print("DEBUG: Initializing Scheduler...")
    # Inicializa o Scheduler (Rotinas e Proatividade Sapiens Fase 4)
    from services.scheduler_service import initialize_scheduler
    initialize_scheduler(app)
    print("DEBUG: Scheduler initialized.")

    print("DEBUG: create_app() finished successfully.")
    return app

def register_api_resources(api):
    from api.resources.company import CompanyListResource, CompanyResource
    from api.resources.project import ProjectListResource, ProjectResource
    from api.resources.project_task import (
        ProjectTaskListResource, ProjectTaskResource, ProjectTaskStageResource,
        ProjectTaskCollaboratorListResource, ProjectTaskCollaboratorResource,
        ProjectTaskHoursSummaryResource, ProjectAllTasksResource, ProjectTaskTransferResource,
        ProjectTaskDependencyListResource, ProjectTaskDependencyResource
    )

    from api.resources.indicator import (
        IndicatorListResource, IndicatorResource, 
        IndicatorGroupListResource,
        IndicatorGoalListResource, IndicatorGoalResource,
        IndicatorDataListResource, IndicatorDataResource
    )
    from api.resources.process import (
        ProcessAreaListResource, ProcessAreaResource,
        MacroProcessListResource, MacroProcessResource,
        ProcessListResource, ProcessResource,
        ProcessRoutineListResource, ProcessRoutineResource,
        ProcessStepListResource, ProcessStepResource,
        ProcessInstanceListResource, ProcessInstanceResource,
        ProcessInstanceWorkLogResource, ActivityWorkLogItemResource
    )
    from api.resources.okr import (
        OKRGlobalListResource, OKRGlobalResource,
        KeyResultListResource, KeyResultResource,
        OKRAreaListResource, OKRAreaResource,
        KeyResultAreaListResource, KeyResultAreaResource
    )
    from api.resources.plan import (
        PlanListResource, PlanResource, 
        PlanDriverResource, PlanDriverDetailResource, PlanSectionStatusResource,
        PlanImplantationResource,
        PlanParticipantListResource, PlanParticipantResource
    )
    from api.resources.incentive import (
        IncentiveIndicatorListResource, IncentiveCalculationResource,
        IncentiveSpiderWebResource, IncentiveRuleResource
    )

    api.add_resource(CompanyListResource, '/api/companies')
    api.add_resource(CompanyResource, '/api/companies/<int:company_id>')
    api.add_resource(ProjectListResource, '/api/projects')
    api.add_resource(ProjectResource, '/api/projects/<int:project_id>')
    api.add_resource(ProjectTaskListResource, '/api/projects/<int:project_id>/tasks')
    api.add_resource(ProjectTaskResource, '/api/projects/<int:project_id>/tasks/<int:task_id>')
    api.add_resource(ProjectTaskStageResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/stage')
    api.add_resource(ProjectTaskCollaboratorListResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/collaborators')
    api.add_resource(ProjectTaskCollaboratorResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/collaborators/<int:collaborator_id>')
    api.add_resource(ProjectTaskHoursSummaryResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/hours-summary')
    api.add_resource(ProjectTaskTransferResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/transfer')
    api.add_resource(ProjectTaskDependencyListResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/dependencies')
    api.add_resource(ProjectTaskDependencyResource, '/api/projects/<int:project_id>/tasks/<int:task_id>/dependencies/<int:dep_id>')
    api.add_resource(ProjectAllTasksResource, '/api/projects/all-tasks')

    api.add_resource(IndicatorListResource, '/api/indicators')
    api.add_resource(IndicatorResource, '/api/indicators/<int:indicator_id>')
    api.add_resource(IndicatorGroupListResource, '/api/indicator-groups')
    api.add_resource(IndicatorGoalListResource, '/api/indicator-goals')
    api.add_resource(IndicatorGoalResource, '/api/indicator-goals/<int:goal_id>')
    api.add_resource(IndicatorDataListResource, '/api/indicator-data')
    api.add_resource(IndicatorDataResource, '/api/indicator-data/<int:data_id>')
    api.add_resource(ProcessAreaListResource, '/api/process-areas')
    api.add_resource(ProcessAreaResource, '/api/process-areas/<int:area_id>')
    api.add_resource(MacroProcessListResource, '/api/macro-processes')
    api.add_resource(MacroProcessResource, '/api/macro-processes/<int:macro_id>')
    api.add_resource(ProcessListResource, '/api/processes', '/api/companies/<int:company_id>/processes')
    api.add_resource(ProcessResource, '/api/processes/<int:process_id>')
    api.add_resource(ProcessRoutineListResource, '/api/process-routines')
    api.add_resource(ProcessRoutineResource, '/api/process-routines/<int:routine_id>')
    api.add_resource(ProcessStepListResource, '/api/process-steps')
    api.add_resource(ProcessStepResource, '/api/process-steps/<int:step_id>')
    api.add_resource(ProcessInstanceListResource, '/api/process-instances', '/api/companies/<int:company_id>/process-instances')
    api.add_resource(ProcessInstanceResource, '/api/process-instances/<int:instance_id>')
    api.add_resource(ProcessInstanceWorkLogResource, '/api/process-instances/<int:instance_id>/work-logs')
    api.add_resource(ActivityWorkLogItemResource, '/api/activity-work-logs/<int:log_id>')
    api.add_resource(OKRGlobalListResource, '/api/okrs-global')
    api.add_resource(OKRGlobalResource, '/api/okrs-global/<int:okr_id>')
    api.add_resource(KeyResultListResource, '/api/key-results')
    api.add_resource(KeyResultResource, '/api/key-results/<int:kr_id>')
    api.add_resource(OKRAreaListResource, '/api/okrs-area')
    api.add_resource(OKRAreaResource, '/api/okrs-area/<int:okr_id>')
    api.add_resource(KeyResultAreaListResource, '/api/key-results-area')
    api.add_resource(KeyResultAreaResource, '/api/key-results-area/<int:kr_id>')

    api.add_resource(PlanListResource, '/api/plans')
    api.add_resource(PlanResource, '/api/plans/<int:plan_id>')
    api.add_resource(PlanDriverResource, '/api/plans/<int:plan_id>/drivers')
    api.add_resource(PlanDriverDetailResource, '/api/plans/<int:plan_id>/drivers/<int:driver_id>')
    api.add_resource(PlanSectionStatusResource, '/api/plans/<int:plan_id>/sections/<string:section_key>/status')
    api.add_resource(PlanImplantationResource, '/api/plans/<int:plan_id>/implantation/<string:section_key>')
    api.add_resource(PlanParticipantListResource, '/api/plans/<int:plan_id>/participants')
    api.add_resource(PlanParticipantResource, '/api/plans/<int:plan_id>/participants/<int:participant_id>')
    
    from api.resources.meeting import (
        MeetingListResource, MeetingResource, MeetingExecutionResource, 
        MeetingStartResource, MeetingFinishResource, MeetingAgendaUseResource,
        MeetingActivitiesResource, MeetingSyncCheckResource, MeetingSyncActivitiesResource,
        MeetingRemoveFromProjectResource
    )
    api.add_resource(MeetingListResource, '/meetings/api/company/<int:company_id>/meeting')
    api.add_resource(MeetingResource, '/meetings/api/meeting/<int:meeting_id>')
    api.add_resource(MeetingExecutionResource, '/meetings/api/meeting/<int:meeting_id>/execucao')
    api.add_resource(MeetingResource, '/meetings/api/meeting/<int:meeting_id>/preliminares', endpoint='meeting_preliminares')
    api.add_resource(MeetingStartResource, '/meetings/api/meeting/<int:meeting_id>/iniciar')
    api.add_resource(MeetingFinishResource, '/meetings/api/meeting/<int:meeting_id>/finalizar')
    api.add_resource(MeetingAgendaUseResource, '/meetings/api/agenda-item/<int:item_id>/use')
    api.add_resource(MeetingActivitiesResource, '/meetings/api/meeting/<int:meeting_id>/atividades')
    api.add_resource(MeetingSyncCheckResource, '/meetings/api/meeting/<int:meeting_id>/check-sync')
    api.add_resource(MeetingSyncActivitiesResource, '/meetings/api/meeting/<int:meeting_id>/sync-activities')
    api.add_resource(MeetingRemoveFromProjectResource, '/meetings/api/meeting/<int:meeting_id>/remove-from-project')
    
    from api.resources.occurrence import OccurrenceListResource, OccurrenceResource
    api.add_resource(OccurrenceListResource, '/api/occurrences')
    api.add_resource(OccurrenceResource, '/api/occurrences/<int:occurrence_id>')

    from api.resources.efficiency import EfficiencyCollaborators
    api.add_resource(EfficiencyCollaborators, '/api/companies/<int:company_id>/efficiency/collaborators')

    # Incentive API
    api.add_resource(IncentiveIndicatorListResource, '/api/incentives/indicators')
    api.add_resource(IncentiveCalculationResource, '/api/incentives/calculate')
    api.add_resource(IncentiveSpiderWebResource, '/api/incentives/spider-web-data')
    api.add_resource(IncentiveRuleResource, '/api/incentives/rule-sets/<int:rule_set_id>/rules')

def register_blueprints(app):
    # Route to serve uploaded files
    @app.route('/uploads/<path:filename>')
    def serve_uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    from api.routes.main import main_bp
    from api.routes.auth import auth_bp
    from api.routes.companies import companies_bp
    from api.routes.projects import projects_bp
    from api.routes.indicators import indicators_bp
    from api.routes.processes import processes_bp
    from api.routes.okr import okr_bp
    from api.routes.my_work import my_work_bp
    from api.routes.diag import diag_bp
    from api.routes.dev import dev_bp
    from api.notes import notes_bp
    from api.routes.agents import agents_bp
    from api.routes.configs import configs_bp
    from api.routes.integrations import integrations_bp
    from api.routes.portfolios import portfolios_bp
    from api.user_employee import user_employee_bp
    from api.routes.meetings import meetings_bp
    # from api.routes.ai_board import ai_board_bp
    from api.routes.onboarding import onboarding_bp
    from api.routes.plans import plans_bp
    from api.routes.users import usuarios_bp
 
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(indicators_bp)
    app.register_blueprint(processes_bp)
    app.register_blueprint(okr_bp)
    app.register_blueprint(my_work_bp)
    app.register_blueprint(diag_bp)
    app.register_blueprint(dev_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(configs_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(portfolios_bp)
    app.register_blueprint(user_employee_bp)
    app.register_blueprint(meetings_bp, url_prefix='/meetings')
    # app.register_blueprint(ai_board_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(usuarios_bp)

    from api.routes.incentives import incentives_bp
    app.register_blueprint(incentives_bp)

    # Webhook Telegram (Sapiens Fase 3)
    from api.webhooks.telegram_webhook import telegram_bp, setup_webhook
    app.register_blueprint(telegram_bp, url_prefix='/webhook')

    # Webhook WhatsApp/Instagram (Sapiens Fase 4)
    from api.webhooks.whatsapp_webhook import whatsapp_webhook_bp
    app.register_blueprint(whatsapp_webhook_bp, url_prefix='/webhook')

    # Webhook Email (Sapiens)
    from api.webhooks.email_webhook import email_webhook_bp
    app.register_blueprint(email_webhook_bp, url_prefix='/webhook')

    # Configuracao automatica do Webhook:
    # - PRODUCAO: permitido normalmente.
    # - DEV: permitido somente com override + token DEV dedicado.
    allow_dev_webhook = os.environ.get('TELEGRAM_ALLOW_DEV_WEBHOOK', 'false').lower() == 'true'
    has_dev_token = bool(os.environ.get('TELEGRAM_BOT_TOKEN_DEV'))
    is_debug = app.config.get('DEBUG', False)
    should_setup_webhook = (not is_debug) or (allow_dev_webhook and has_dev_token)

    if app.config.get('TELEGRAM_SETUP_WEBHOOK') and app.config.get('EXTERNAL_URL') and should_setup_webhook:
        print(f"BOT [TELEGRAM] Verificando registro de Webhook para: {app.config.get('EXTERNAL_URL')}")
        setup_webhook(app.config.get('EXTERNAL_URL'))
    elif is_debug and app.config.get('TELEGRAM_SETUP_WEBHOOK') and not has_dev_token:
        print("BOT [TELEGRAM] DEV sem TELEGRAM_BOT_TOKEN_DEV: webhook nao sera registrado para evitar mistura com producao.")

if __name__ == '__main__':
    app = create_app()
    print("Starting APP32 modularized version...")
    app.run(debug=True, port=5032)
