from datetime import date
from pathlib import Path
from types import SimpleNamespace

from flask import Blueprint, Flask, render_template
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader


def _format_currency_br(value):
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def test_contract_billing_review_template_iterates_preview_items_key():
    app = Flask(__name__)
    app.secret_key = "test"
    app.jinja_loader = ChoiceLoader(
        [
            DictLoader(
                {
                    "layouts/base.html": "{% block layout %}{% endblock %}",
                    "layouts/workspace.html": "{% block workspace_content %}{% endblock %}",
                    "modules/contracts/_styles.html": "",
                }
            ),
            FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")),
        ]
    )
    app.jinja_env.filters["format_currency_br"] = _format_currency_br

    contracts_bp = Blueprint("contracts", __name__)

    @contracts_bp.route("/contracts/billing/review")
    def contracts_billing_review():
        return ""

    app.register_blueprint(contracts_bp)

    contract = SimpleNamespace(
        id=39,
        code="AL.N.035",
        title="Contrato teste",
        party=SimpleNamespace(name="Cliente teste"),
    )
    row = {
        "contract": contract,
        "preview": {
            "competence_start": date(2026, 6, 1),
            "competence_end": date(2026, 6, 30),
            "issue_date": date(2026, 6, 6),
            "due_date": date(2026, 7, 31),
            "gross_amount": 4494.35,
            "retention_amount": 112.36,
            "net_amount": 4381.99,
            "items": [
                {
                    "contract_item_id": 37,
                    "item_code": "1.10.1010",
                    "description": "Tratamento de Água",
                    "gross_amount": 4494.35,
                    "retention_amount": 112.36,
                    "net_amount": 4381.99,
                    "retention_details": [
                        {"label": "ISS", "kind": "iss", "calculated_amount": 112.36}
                    ],
                }
            ],
        },
        "eligibility": {"eligible": True, "reasons": []},
        "review_notes": "",
    }

    with app.test_request_context("/contracts/billing/review?company_id=1&contract_ids=39"):
        html = render_template(
            "modules/contracts/contracts_billing_review.html",
            company_id=1,
            review_rows=[row],
            contract_ids=[39],
        )

    assert "Tratamento de Água" in html
    assert 'name="item_ids_39" value="37"' in html


def test_contract_spot_billing_review_template_uses_billing_item_ids():
    app = Flask(__name__)
    app.secret_key = "test"
    app.jinja_loader = ChoiceLoader(
        [
            DictLoader(
                {
                    "layouts/base.html": "{% block layout %}{% endblock %}",
                    "layouts/workspace.html": "{% block workspace_content %}{% endblock %}",
                    "modules/contracts/_styles.html": "",
                }
            ),
            FileSystemLoader(str(Path(__file__).resolve().parents[1] / "templates")),
        ]
    )
    app.jinja_env.filters["format_currency_br"] = _format_currency_br

    contracts_bp = Blueprint("contracts", __name__)

    @contracts_bp.route("/contracts/billing/spot/review")
    def contracts_billing_spot_review():
        return ""

    app.register_blueprint(contracts_bp)

    contract = SimpleNamespace(
        id=41,
        code="AL.N.041",
        title="Contrato spot",
        party=SimpleNamespace(name="Cliente spot"),
    )
    row = {
        "contract": contract,
        "preview": {
            "competence_start": date(2026, 6, 12),
            "competence_end": date(2026, 6, 12),
            "issue_date": date(2026, 6, 12),
            "due_date": date(2026, 6, 30),
            "gross_amount": 1500.00,
            "retention_amount": 0,
            "net_amount": 1500.00,
            "items": [
                {
                    "contract_billing_item_id": 88,
                    "item_code": "SPOT.088",
                    "description": "Diagnóstico pontual",
                    "gross_amount": 1500.00,
                    "retention_amount": 0,
                    "net_amount": 1500.00,
                    "retention_details": [],
                }
            ],
        },
        "eligibility": {"eligible": True, "reasons": []},
        "review_notes": "",
    }

    with app.test_request_context("/contracts/billing/spot/review?company_id=1&contract_ids=41"):
        html = render_template(
            "modules/contracts/contracts_billing_review.html",
            company_id=1,
            review_rows=[row],
            contract_ids=[41],
            billing_mode="spot_services",
        )

    assert "Conferência de Serviços Pontuais" in html
    assert 'name="billing_item_ids_41" value="88"' in html
