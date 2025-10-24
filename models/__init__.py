from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def init_app(app):
    """Initialize extensions with app"""
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    # Import models to register them
    from . import user, company, plan, participant, company_data
    from . import driver_topic, okr_global
    from . import okr_area, project, ai_agent, user_log
    from . import team, activity_work_log, activity_comment
    
    return db, login_manager, migrate
