import os
import sys

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes.my_work import my_work_bp
from api.routes.portfolios import portfolios_bp
from api.routes.projects import projects_bp


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    app.register_blueprint(projects_bp)
    app.register_blueprint(my_work_bp)
    app.register_blueprint(portfolios_bp)
    return app


def test_summary_pdf_alias_routes_are_registered():
    app = _build_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/projects/<int:project_id>/summary-pdf" in rules
    assert "/api/projects/<int:project_id>/summary.pdf" in rules
    assert "/my-work/api/project-task/<int:task_id>/summary-pdf" in rules
    assert "/my-work/api/project-task/<int:task_id>/summary.pdf" in rules
    assert "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>/summary-pdf" in rules
    assert "/api/companies/<int:company_id>/portfolios/<int:portfolio_id>/summary.pdf" in rules
