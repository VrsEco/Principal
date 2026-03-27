from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_restful import Api
import os
from sqlalchemy import inspect, or_, text

from models import db
from schemas import ma
from utils.error_handling import register_global_error_handlers


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

    @app.template_filter('format_currency_br')
    def format_currency_br_filter(value):
        from utils.jinja_filters import format_currency_br
        return format_currency_br(value)

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
    register_global_error_handlers(app)

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
            if "indicators" in table_names:
                indicator_columns = {col["name"] for col in inspector.get_columns("indicators")}
                with db.engine.begin() as conn:
                    if "indicator_type" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN indicator_type VARCHAR(50) NOT NULL DEFAULT 'result'"))
                    if "source_module" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN source_module VARCHAR(50) NOT NULL DEFAULT 'manual'"))
                    if "source_id" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN source_id INTEGER"))
                    if "source_scope" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN source_scope VARCHAR(50) NOT NULL DEFAULT 'company'"))
                        print("DEBUG: indicators.source_scope column added successfully.")
                    if "source_config" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN source_config JSON"))
                        print("DEBUG: indicators.source_config column added successfully.")
                    if "collection_mode" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN collection_mode VARCHAR(30) NOT NULL DEFAULT 'manual'"))
                    if "aggregation_function" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN aggregation_function VARCHAR(30) NOT NULL DEFAULT 'sum'"))
                    if "unit" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN unit VARCHAR(50) DEFAULT 'pts'"))
                    if "polarity" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN polarity VARCHAR(20) DEFAULT 'positive'"))
                    if "measurement_frequency" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN measurement_frequency VARCHAR(30) DEFAULT 'monthly'"))
                    if "formula" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN formula TEXT"))
                    if "process_id" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN process_id INTEGER REFERENCES processes(id)"))
                    if "project_id" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
                    if "responsible_id" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN responsible_id INTEGER REFERENCES employees(id)"))
                    if "collaborators" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN collaborators JSON"))
                    if "data_source" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN data_source TEXT"))
                    if "notes" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN notes TEXT"))
                    if "okr_reference" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN okr_reference VARCHAR(255)"))
                    if "okr_level" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN okr_level VARCHAR(50)"))
                    if "is_active" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                    if "routine_id" not in indicator_columns:
                        conn.execute(text("ALTER TABLE indicators ADD COLUMN routine_id INTEGER REFERENCES routines(id)"))
            if "indicator_data" in table_names:
                indicator_data_columns = {col["name"] for col in inspector.get_columns("indicator_data")}
                with db.engine.begin() as conn:
                    if "indicator_id" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN indicator_id INTEGER"))
                        conn.execute(text("""
                            UPDATE indicator_data
                            SET indicator_id = indicator_goals.indicator_id
                            FROM indicator_goals
                            WHERE indicator_data.goal_id = indicator_goals.id
                              AND indicator_data.indicator_id IS NULL
                        """))
                        print("DEBUG: indicator_data.indicator_id column added successfully.")
                    if "record_date" in indicator_data_columns and "measured_date" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data RENAME COLUMN record_date TO measured_date"))
                        print("DEBUG: indicator_data.record_date renamed to measured_date.")
                    if "value" in indicator_data_columns and "measured_value" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data RENAME COLUMN value TO measured_value"))
                        conn.execute(text("ALTER TABLE indicator_data ALTER COLUMN measured_value TYPE NUMERIC(15, 4) USING measured_value::numeric"))
                        print("DEBUG: indicator_data.value renamed to measured_value.")
                    if "period_start" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN period_start DATE"))
                    if "period_end" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN period_end DATE"))
                    if "employee_id" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN employee_id INTEGER REFERENCES employees(id)"))
                    if "collaborator_id" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN collaborator_id INTEGER REFERENCES employees(id)"))
                    if "source_ref" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN source_ref VARCHAR(255)"))
                    if "evidence_payload" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN evidence_payload JSON"))
                    if "routine_id" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN routine_id INTEGER REFERENCES routines(id)"))
                    if "process_instance_id" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN process_instance_id INTEGER REFERENCES process_instances(id)"))
                    if "status" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN status VARCHAR(30) DEFAULT 'draft'"))
                    if "is_manual" not in indicator_data_columns:
                        conn.execute(text("ALTER TABLE indicator_data ADD COLUMN is_manual BOOLEAN DEFAULT FALSE"))
            if "indicator_goals" in table_names:
                indicator_goal_columns = {col["name"] for col in inspector.get_columns("indicator_goals")}
                with db.engine.begin() as conn:
                    if "performance_ranges" not in indicator_goal_columns:
                        conn.execute(text("ALTER TABLE indicator_goals ADD COLUMN performance_ranges JSON"))
                    if "routine_id" not in indicator_goal_columns:
                        conn.execute(text("ALTER TABLE indicator_goals ADD COLUMN routine_id INTEGER REFERENCES routines(id)"))
                    if "collection_method" not in indicator_goal_columns:
                        conn.execute(text("ALTER TABLE indicator_goals ADD COLUMN collection_method VARCHAR(50) DEFAULT 'manual'"))
            if "incentive_rules" in table_names:
                incentive_rule_columns = {col["name"] for col in inspector.get_columns("incentive_rules")}
                with db.engine.begin() as conn:
                    if "impact_value" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN impact_value NUMERIC(15, 4) DEFAULT 1.0"))
                    if "weight" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN weight NUMERIC(10, 4) DEFAULT 1.0"))
                    if "use_indicator_goal" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN use_indicator_goal BOOLEAN DEFAULT TRUE"))
                    if "calculation_mode" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN calculation_mode VARCHAR(30) DEFAULT 'ranges'"))
                    if "ranges_config" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN ranges_config JSON"))
                    if "target_value" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN target_value NUMERIC(15, 4)"))
                    if "min_threshold" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN min_threshold NUMERIC(15, 4)"))
                    if "max_cap" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN max_cap NUMERIC(15, 4)"))
                    if "max_reduction" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN max_reduction NUMERIC(15, 4)"))
                    if "impact_type" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN impact_type VARCHAR(20) DEFAULT 'multiplier'"))
                    if "order_index" not in incentive_rule_columns:
                        conn.execute(text("ALTER TABLE incentive_rules ADD COLUMN order_index INTEGER DEFAULT 0"))
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
        IndicatorDataListResource, IndicatorDataResource,
        IndicatorDataBatchResource
    )
    from api.resources.process import (
        ProcessAreaListResource, ProcessAreaResource,
        MacroProcessListResource, MacroProcessResource,
        ProcessListResource, ProcessResource,
        ProcessRoutineListResource, ProcessRoutineResource,
        ProcessScheduleListResource,
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
    from api.resources.financial import (
        FinancialEntryListResource,
        FinancialDirectEntryOptionsResource,
        FinancialDirectEntryCreateResource,
        FinancialBankTransferOptionsResource,
        FinancialBankTransferListResource,
        FinancialBankTransferResource,
        FinancialNonFinancialLaunchOptionsResource,
        FinancialNonFinancialLaunchListResource,
        FinancialNonFinancialLaunchResource,
        FinancialCatalogListResource,
        FinancialCatalogResource,
        FinancialCatalogToggleResource,
        FinancialDomainEnablementListResource,
        FinancialDomainEnablementResource,
        FinancialDomainEnablementToggleResource,
        FinancialIngestionRecordListResource,
        FinancialIngestionRecordResource,
        FinancialIngestionRecordReviewResource,
        FinancialIngestionRecordConvertResource,
        FinancialScheduleListResource,
        FinancialScheduleOptionsResource,
        FinancialScheduleResource,
        FinancialScheduleToggleResource,
        FinancialScheduleGenerateResource,
        FinancialScheduleCreateEntryResource,
        FinancialScheduleAttachmentListResource,
        FinancialScheduleAttachmentResource,
        FinancialAutomationRuleListResource,
        FinancialAutomationRuleResource,
        FinancialAutomationExecutionListResource,
        FinancialAutomationApplyInstanceResource,
        FinancialProcessTriggerDispatchResource,
        FinancialEntryResource,
        FinancialEntryAllocationListResource,
        FinancialEntrySettlementListResource,
        FinancialSettlementResource,
        FinancialImportBatchListResource,
        FinancialImportBatchResource,
        FinancialImportBatchProcessResource,
        FinancialImportBatchReconcileResource,
        FinancialReconciliationMatchReviewResource,
        FinancialClassificationRuleListResource,
        FinancialClassificationRuleResource,
        FinancialClassificationRuleToggleResource,
        FinancialImportBatchClassifyResource,
        FinancialClassificationMemoryListResource,
        FinancialClassificationMemoryResource,
        FinancialClassificationMemoryToggleResource,
        FinancialImportBatchSuggestionResource,
        FinancialClassificationSuggestionListResource,
        FinancialClassificationSuggestionReviewResource,
        FinancialImportBatchAIRankingResource,
        FinancialClassificationPendingQueueResource,
        FinancialClassificationDashboardResource,
        FinancialClassificationAskUserResource,
        FinancialClassificationResolveAnswerResource,
        FinancialClosingListResource,
        FinancialClosingPreviewResource,
        FinancialReportTypeListResource,
        FinancialReportGenerateResource,
        FinancialExecutiveDashboardResource,
    )
    from api.resources.financial_budget import (
        FinancialBudgetVersionListResource,
        FinancialBudgetVersionResource,
        FinancialBudgetMatrixResource,
        FinancialBudgetOptionsResource,
        FinancialBudgetImportResource,
        FinancialBudgetVersionDuplicateResource,
        FinancialBudgetPlanningWorkspaceResource,
        FinancialBudgetExecutionWorkspaceResource,
        FinancialBudgetLineListResource,
        FinancialBudgetLineResource,
        FinancialBudgetContractListResource,
        FinancialBudgetContractResource,
        FinancialBudgetDocumentListResource,
        FinancialBudgetDocumentResource,
        FinancialBudgetDocumentScheduleListResource,
        FinancialBudgetDocumentScheduleResource,
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
    api.add_resource(IndicatorDataBatchResource, '/api/indicator-data/batch')
    api.add_resource(IndicatorDataResource, '/api/indicator-data/<int:data_id>')
    api.add_resource(ProcessAreaListResource, '/api/process-areas')
    api.add_resource(ProcessAreaResource, '/api/process-areas/<int:area_id>')
    api.add_resource(MacroProcessListResource, '/api/macro-processes')
    api.add_resource(MacroProcessResource, '/api/macro-processes/<int:macro_id>')
    api.add_resource(ProcessListResource, '/api/processes', '/api/companies/<int:company_id>/processes')
    api.add_resource(ProcessResource, '/api/processes/<int:process_id>')
    api.add_resource(ProcessRoutineListResource, '/api/process-routines')
    api.add_resource(ProcessRoutineResource, '/api/process-routines/<int:routine_id>')
    api.add_resource(ProcessScheduleListResource, '/api/process-schedules')
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
        MeetingRemoveFromProjectResource, MeetingSummaryRecipientsResource,
        MeetingShareSummaryResource
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
    api.add_resource(MeetingSummaryRecipientsResource, '/meetings/api/meeting/<int:meeting_id>/summary-recipients')
    api.add_resource(MeetingShareSummaryResource, '/meetings/api/meeting/<int:meeting_id>/share-summary')
    
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
    api.add_resource(FinancialEntryListResource, '/api/financial/entries')
    api.add_resource(FinancialDirectEntryOptionsResource, '/api/financial/entries/direct/options')
    api.add_resource(FinancialDirectEntryCreateResource, '/api/financial/entries/direct')
    api.add_resource(FinancialBankTransferOptionsResource, '/api/financial/bank-transfers/options')
    api.add_resource(FinancialBankTransferListResource, '/api/financial/bank-transfers')
    api.add_resource(FinancialBankTransferResource, '/api/financial/bank-transfers/<int:transfer_id>')
    api.add_resource(FinancialNonFinancialLaunchOptionsResource, '/api/financial/non-financial-entries/options')
    api.add_resource(FinancialNonFinancialLaunchListResource, '/api/financial/non-financial-entries')
    api.add_resource(FinancialNonFinancialLaunchResource, '/api/financial/non-financial-entries/<int:launch_id>')
    api.add_resource(FinancialCatalogListResource, '/api/financial/catalogs/<string:catalog_type>')
    api.add_resource(FinancialCatalogResource, '/api/financial/catalogs/<string:catalog_type>/<int:item_id>')
    api.add_resource(FinancialCatalogToggleResource, '/api/financial/catalogs/<string:catalog_type>/<int:item_id>/toggle')
    api.add_resource(FinancialDomainEnablementListResource, '/api/financial/domain-enablements')
    api.add_resource(FinancialDomainEnablementResource, '/api/financial/domain-enablements/<string:domain_type>/<int:source_id>')
    api.add_resource(FinancialDomainEnablementToggleResource, '/api/financial/domain-enablements/<string:domain_type>/<int:source_id>/toggle')
    api.add_resource(FinancialIngestionRecordListResource, '/api/financial/ingestions')
    api.add_resource(FinancialIngestionRecordResource, '/api/financial/ingestions/<int:record_id>')
    api.add_resource(FinancialIngestionRecordReviewResource, '/api/financial/ingestions/<int:record_id>/review')
    api.add_resource(FinancialIngestionRecordConvertResource, '/api/financial/ingestions/<int:record_id>/convert')
    api.add_resource(FinancialScheduleListResource, '/api/financial/schedules')
    api.add_resource(FinancialScheduleOptionsResource, '/api/financial/schedules/options')
    api.add_resource(FinancialScheduleResource, '/api/financial/schedules/<int:schedule_id>')
    api.add_resource(FinancialScheduleToggleResource, '/api/financial/schedules/<int:schedule_id>/toggle')
    api.add_resource(FinancialScheduleGenerateResource, '/api/financial/schedules/generate-due')
    api.add_resource(FinancialScheduleCreateEntryResource, '/api/financial/schedules/<int:schedule_id>/create-entry')
    api.add_resource(FinancialScheduleAttachmentListResource, '/api/financial/schedules/<int:schedule_id>/attachments')
    api.add_resource(FinancialScheduleAttachmentResource, '/api/financial/schedules/<int:schedule_id>/attachments/<string:attachment_id>')
    api.add_resource(FinancialAutomationRuleListResource, '/api/financial/automation-rules')
    api.add_resource(FinancialAutomationRuleResource, '/api/financial/automation-rules/<int:rule_id>')
    api.add_resource(FinancialAutomationExecutionListResource, '/api/financial/automation-executions')
    api.add_resource(FinancialAutomationApplyInstanceResource, '/api/financial/automation-rules/<int:rule_id>/apply/<int:process_instance_id>')
    api.add_resource(FinancialProcessTriggerDispatchResource, '/api/financial/process-triggers/<int:process_instance_id>/dispatch')
    api.add_resource(FinancialEntryResource, '/api/financial/entries/<int:entry_id>')
    api.add_resource(FinancialEntryAllocationListResource, '/api/financial/entries/<int:entry_id>/allocations')
    api.add_resource(FinancialEntrySettlementListResource, '/api/financial/entries/<int:entry_id>/settlements')
    api.add_resource(FinancialSettlementResource, '/api/financial/settlements/<int:settlement_id>')
    api.add_resource(FinancialImportBatchListResource, '/api/financial/imports')
    api.add_resource(FinancialImportBatchResource, '/api/financial/imports/<int:batch_id>')
    api.add_resource(FinancialImportBatchProcessResource, '/api/financial/imports/<int:batch_id>/process')
    api.add_resource(FinancialImportBatchClassifyResource, '/api/financial/imports/<int:batch_id>/classify')
    api.add_resource(FinancialImportBatchSuggestionResource, '/api/financial/imports/<int:batch_id>/suggest-classification')
    api.add_resource(FinancialImportBatchAIRankingResource, '/api/financial/imports/<int:batch_id>/ai-rank-classification')
    api.add_resource(FinancialImportBatchReconcileResource, '/api/financial/imports/<int:batch_id>/reconcile')
    api.add_resource(FinancialReconciliationMatchReviewResource, '/api/financial/reconciliation-matches/<int:match_id>/review')
    api.add_resource(FinancialClassificationRuleListResource, '/api/financial/classification-rules')
    api.add_resource(FinancialClassificationRuleResource, '/api/financial/classification-rules/<int:rule_id>')
    api.add_resource(FinancialClassificationRuleToggleResource, '/api/financial/classification-rules/<int:rule_id>/toggle')
    api.add_resource(FinancialClassificationMemoryListResource, '/api/financial/classification-memories')
    api.add_resource(FinancialClassificationMemoryResource, '/api/financial/classification-memories/<int:memory_id>')
    api.add_resource(FinancialClassificationMemoryToggleResource, '/api/financial/classification-memories/<int:memory_id>/toggle')
    api.add_resource(FinancialClassificationSuggestionListResource, '/api/financial/classification-suggestions')
    api.add_resource(FinancialClassificationSuggestionReviewResource, '/api/financial/classification-suggestions/<int:suggestion_id>/review')
    api.add_resource(FinancialClassificationPendingQueueResource, '/api/financial/classification-pending')
    api.add_resource(FinancialClassificationDashboardResource, '/api/financial/classification-dashboard')
    api.add_resource(FinancialClassificationAskUserResource, '/api/financial/classification-pending/<int:import_row_id>/ask-user')
    api.add_resource(FinancialClassificationResolveAnswerResource, '/api/financial/classification-pending/<int:import_row_id>/resolve')
    api.add_resource(FinancialClosingListResource, '/api/financial/closings')
    api.add_resource(FinancialClosingPreviewResource, '/api/financial/closings/preview')
    api.add_resource(FinancialReportTypeListResource, '/api/financial/reports/types')
    api.add_resource(FinancialReportGenerateResource, '/api/financial/reports/generate')
    api.add_resource(FinancialExecutiveDashboardResource, '/api/financial/dashboard')
    api.add_resource(FinancialBudgetVersionListResource, '/api/financial/budget/versions')
    api.add_resource(FinancialBudgetVersionResource, '/api/financial/budget/versions/<int:version_id>')
    api.add_resource(FinancialBudgetMatrixResource, '/api/financial/budget/versions/<int:version_id>/matrix')
    api.add_resource(FinancialBudgetImportResource, '/api/financial/budget/versions/<int:version_id>/import')
    api.add_resource(FinancialBudgetVersionDuplicateResource, '/api/financial/budget/versions/<int:version_id>/duplicate')
    api.add_resource(FinancialBudgetPlanningWorkspaceResource, '/api/financial/budget/workspace')
    api.add_resource(FinancialBudgetExecutionWorkspaceResource, '/api/financial/budget/execution-workspace')
    api.add_resource(FinancialBudgetOptionsResource, '/api/financial/budget/options')
    api.add_resource(FinancialBudgetLineListResource, '/api/financial/budget/versions/<int:version_id>/lines')
    api.add_resource(FinancialBudgetLineResource, '/api/financial/budget/lines/<int:line_id>')
    api.add_resource(FinancialBudgetContractListResource, '/api/financial/budget/lines/<int:line_id>/contracts')
    api.add_resource(FinancialBudgetContractResource, '/api/financial/budget/contracts/<int:contract_id>')
    api.add_resource(FinancialBudgetDocumentListResource, '/api/financial/budget/contracts/<int:contract_id>/documents')
    api.add_resource(FinancialBudgetDocumentResource, '/api/financial/budget/documents/<int:document_id>')
    api.add_resource(FinancialBudgetDocumentScheduleListResource, '/api/financial/budget/documents/<int:document_id>/schedules')
    api.add_resource(FinancialBudgetDocumentScheduleResource, '/api/financial/budget/documents/<int:document_id>/schedules/<int:schedule_id>')

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
    from api.routes.financial import financial_bp
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
    app.register_blueprint(financial_bp)
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
