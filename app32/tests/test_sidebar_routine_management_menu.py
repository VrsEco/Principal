import os
import sys

from flask import Blueprint, Flask, render_template_string

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )
    app.config["SECRET_KEY"] = "test"

    processes_bp = Blueprint("processes", __name__)
    projects_bp = Blueprint("projects", __name__)
    portfolios_bp = Blueprint("portfolios", __name__)
    meetings_bp = Blueprint("meetings", __name__)

    @processes_bp.route("/process-map")
    def process_map():
        return "ok"

    @processes_bp.route("/processes")
    def processes_list():
        return "ok"

    @processes_bp.route("/process-routines")
    def process_routines_redirect():
        return "ok"

    @processes_bp.route("/process-instances")
    def process_instances_redirect():
        return "ok"

    @processes_bp.route("/process-occurrences")
    def process_occurrences_redirect():
        return "ok"

    @projects_bp.route("/projects")
    def projects_list():
        return "ok"

    @projects_bp.route("/projects/analysis")
    def project_analysis():
        return "ok"

    @portfolios_bp.route("/project-portfolios")
    def portfolios_page_redirect():
        return "ok"

    @meetings_bp.route("/")
    def meetings_manage_root():
        return "ok"

    app.register_blueprint(processes_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(portfolios_bp)
    app.register_blueprint(meetings_bp, url_prefix="/meetings")
    return app


def _render_menu(app, path: str) -> str:
    with app.test_request_context(path):
        return render_template_string("{% include 'partials/sidebar/_routine_management.html' %}")


def test_routine_menu_structure_matches_sidebar_tree():
    app = _build_app()

    html = _render_menu(app, "/process-map")

    assert "Gestão da Rotina" in html
    assert "Gestão de Processos" in html
    assert "Arquitetura de Processos" in html
    assert "Modelagem de Processos" in html
    assert "Rotina de Processos" in html
    assert "Instâncias de Processos" in html
    assert "Gestão de Projetos" in html
    assert "Portfólio de Projetos" in html
    assert "Projetos" in html
    assert "Análise de Projetos" in html
    assert "Gestão de Reuniões" in html
    assert "Gestão de Ocorrências" in html
    assert "Análise da Rotina" not in html
    assert "Análise de Eficiência" not in html


def test_process_routine_pages_keep_process_group_open():
    app = _build_app()

    html = _render_menu(app, "/companies/9/routines/20")

    assert 'Gestão de Processos' in html
    assert 'Rotina de Processos' in html
    assert 'sidebar-group open' in html
    assert 'sidebar-subgroup open' in html
    assert 'Rotina de Processos\n                </a>' in html
    assert 'active' in html


def test_project_portfolio_page_opens_project_group():
    app = _build_app()

    html = _render_menu(app, "/companies/9/project-portfolios")

    assert 'Gestão de Projetos' in html
    assert 'sidebar-group open' in html
    assert 'Portfólio de Projetos' in html
    assert '/project-portfolios' in html
