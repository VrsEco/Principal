from pathlib import Path
import sys
from types import SimpleNamespace

from flask import Blueprint, Flask, render_template
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.routes import contracts as contracts_route


def _format_currency_br(value):
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def test_contracts_billing_filters_from_request_reads_issuer_legal_entity():
    app = Flask(__name__)

    with app.test_request_context(
        "/contracts/billing?company_id=1&status=active&party_id=9&manager_employee_id=4&contracting_legal_entity_id=7&search=alpha&billing_state=all"
    ):
        filters = contracts_route._contracts_billing_filters_from_request()

    assert filters == {
        "status": "active",
        "party_id": 9,
        "manager_employee_id": 4,
        "contracting_legal_entity_id": 7,
        "search": "alpha",
        "billing_state": "all",
    }


def test_contract_billing_template_renders_issuer_filter():
    app = Flask(__name__)
    app.secret_key = "test"
    app.jinja_env.filters["format_currency_br"] = _format_currency_br
    app.jinja_loader = ChoiceLoader(
        [
            DictLoader(
                {
                    "layouts/base.html": "{% block layout %}{% endblock %}",
                    "layouts/workspace.html": "{% block workspace_content %}{% endblock %}{% block sidebar_right %}{% endblock %}",
                    "modules/contracts/_styles.html": "",
                }
            ),
            FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")),
        ]
    )

    contracts_bp = Blueprint("contracts", __name__)

    @contracts_bp.route("/contracts/billing")
    def contracts_billing_workspace():
        return ""

    app.register_blueprint(contracts_bp)

    with app.test_request_context("/contracts/billing?company_id=1&contracting_legal_entity_id=7"):
        html = render_template(
            "modules/contracts/contracts_billing.html",
            company_id=1,
            company=SimpleNamespace(id=1),
            billing_rows=[],
            parties=[],
            legal_entities=[SimpleNamespace(id=7, code="PJ.007", legal_name="Versus Emitente LTDA")],
            managers=[],
            filters={"contracting_legal_entity_id": 7, "billing_state": "eligible"},
            kpis={"active": 0, "pending_billing": 0, "total": 0},
        )

    assert 'name="contracting_legal_entity_id"' in html
    assert "PJ emissora" in html
    assert "PJ.007 · Versus Emitente LTDA" in html
    assert 'value="7" selected' in html


def test_contract_spot_billing_template_renders_split_labels():
    app = Flask(__name__)
    app.secret_key = "test"
    app.jinja_env.filters["format_currency_br"] = _format_currency_br
    app.jinja_loader = ChoiceLoader(
        [
            DictLoader(
                {
                    "layouts/base.html": "{% block layout %}{% endblock %}",
                    "layouts/workspace.html": "{% block workspace_content %}{% endblock %}{% block sidebar_right %}{% endblock %}",
                    "modules/contracts/_styles.html": "",
                }
            ),
            FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")),
        ]
    )

    contracts_bp = Blueprint("contracts", __name__)

    @contracts_bp.route("/contracts/billing/spot")
    def contracts_billing_spot_workspace():
        return ""

    @contracts_bp.route("/contracts/billing")
    def contracts_billing_workspace():
        return ""

    app.register_blueprint(contracts_bp)

    with app.test_request_context("/contracts/billing/spot?company_id=1"):
        html = render_template(
            "modules/contracts/contracts_billing.html",
            company_id=1,
            company=SimpleNamespace(id=1),
            billing_rows=[],
            parties=[],
            legal_entities=[],
            managers=[],
            filters={"billing_state": "eligible"},
            kpis={"active": 0, "pending_billing": 0, "total": 0},
            billing_mode="spot_services",
        )

    assert "Faturar Serv. Pontuais" in html
    assert "Faturar Contr. Mensais" in html
