from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_restful import Api
import os

from models import db
from schemas import ma

def create_app(config_name=None):
    app = Flask(__name__)
    CORS(app)

    # Configuration
    from config import config as app_configs
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app.config.from_object(app_configs[config_name])
    
    # Ensure Upload Dirs (keep hardcoded if not in config)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Extensions
    db.init_app(app)
    ma.init_app(app)

    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.query.get(int(user_id))

    # RESTful API
    api = Api(app)
    register_api_resources(api)

    # Blueprints
    register_blueprints(app)

    # Ensure Upload Dirs
    for folder in ['flows', 'pop']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_permissions():
        from utils.permissions import has_permission
        from flask import session
        from flask_login import current_user
        
        def check_perm(resource, action, company_id=None):
            if not current_user.is_authenticated:
                return False
            if current_user.role == 'admin':
                return True
            
            # Use active company from session if not provided
            cid = company_id or session.get('active_company_id')
            
            if cid:
                return has_permission(cid, resource, action)
            
            # If no company context, check if they have permission in ANY associated company
            from models import Employee
            user_employees = Employee.query.filter_by(user_id=current_user.id).all()
            for emp in user_employees:
                if has_permission(emp.company_id, resource, action):
                    return True
            return False
            
        return dict(has_permission=check_perm)

    @app.before_request
    def enforce_login():
        from flask import request, redirect, url_for, jsonify, session
        from flask_login import current_user

        # Public endpoints that don't require authentication
        public_endpoints = ['auth.login', 'static', 'dev.seed_demo', 'dev.debug_routes']
        
        # 1. Check if user is authenticated
        if not current_user.is_authenticated:
            if request.endpoint and request.endpoint not in public_endpoints:
                # If it's an API call, return 401
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Authentication required"}), 401
                # Otherwise redirect to login
                return redirect(url_for('auth.login'))
        
        # 2. If authenticated, ensure company is selected
        else:
            # Endpoints allowed without selecting a company
            allowed_post_login = ['auth.portal', 'auth.logout', 'static', 'dev.seed_demo', 'dev.debug_routes']
            
            active_company_id = session.get('active_company_id')
            # Normalize 'null' and 'undefined' strings that might come from frontend/session issues
            if str(active_company_id).lower() in ['null', 'undefined', 'none', '']:
                active_company_id = None
            
            if not active_company_id:
                if request.endpoint and request.endpoint not in allowed_post_login:
                    # Redirect to selection page for UI routes
                    if not request.path.startswith('/api/'):
                        return redirect(url_for('auth.portal'))

    return app

def register_api_resources(api):
    from api.resources.company import CompanyListResource, CompanyResource
    from api.resources.project import ProjectListResource, ProjectResource
    from api.resources.plan import PlanListResource
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
        ProcessScheduleListResource
    )
    from api.resources.okr import (
        OKRGlobalListResource, OKRGlobalResource,
        KeyResultListResource, KeyResultResource,
        OKRAreaListResource, OKRAreaResource
    )

    api.add_resource(CompanyListResource, '/api/companies')
    api.add_resource(CompanyResource, '/api/companies/<int:company_id>')
    api.add_resource(ProjectListResource, '/api/projects')
    api.add_resource(ProjectResource, '/api/projects/<int:project_id>')
    api.add_resource(PlanListResource, '/api/plans')
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
    api.add_resource(ProcessScheduleListResource, '/api/process-schedules')
    api.add_resource(OKRGlobalListResource, '/api/okrs-global')
    api.add_resource(OKRGlobalResource, '/api/okrs-global/<int:okr_id>')
    api.add_resource(KeyResultListResource, '/api/key-results')
    api.add_resource(KeyResultResource, '/api/key-results/<int:kr_id>')
    api.add_resource(OKRAreaListResource, '/api/okrs-area')
    api.add_resource(OKRAreaResource, '/api/okrs-area/<int:okr_id>')

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


app = create_app()

if __name__ == '__main__':
    print("Starting APP32 modularized version...")
    app.run(debug=True, port=5032)
