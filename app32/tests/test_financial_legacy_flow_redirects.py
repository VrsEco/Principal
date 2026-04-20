import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.resources import financial as financial_resource
from api.routes import financial as financial_route


def _build_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["LOGIN_DISABLED"] = True
    app.register_blueprint(financial_route.financial_bp)
    return app


def test_financial_entry_manage_redirects_linked_entry_to_title_flow(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(
        financial_route,
        "_get_entry_with_access",
        lambda entry_id: SimpleNamespace(
            id=88,
            company_id=9,
            financial_schedule_id=15,
            external_reference="financial_schedule:15",
        ),
    )

    with app.test_request_context("/financial/entries/88?company_id=9", method="GET"):
        response = financial_route.financial_entry_manage.__wrapped__(88)

    assert response.status_code == 302
    assert response.location.endswith("/financial/schedules/15?company_id=9&open_tab=baixas&entry_id=88")


def test_entry_settlement_post_blocks_legacy_manual_flow_for_linked_title(monkeypatch):
    app = _build_app()

    class _Column:
        def __eq__(self, other):
            return ("eq", other)

        def is_(self, other):
            return ("is", other)

    class _QueryStub:
        def filter(self, *args, **kwargs):
            return self

        def first_or_404(self):
            return SimpleNamespace(
                id=88,
                company_id=9,
                financial_schedule_id=15,
                external_reference="financial_schedule:15",
            )

    entry_model = type(
        "FinancialEntryStub",
        (),
        {
            "id": _Column(),
            "company_id": _Column(),
            "deleted_at": _Column(),
            "query": _QueryStub(),
        },
    )

    monkeypatch.setattr(financial_resource, "FinancialEntry", entry_model)
    monkeypatch.setattr(financial_resource, "get_request_company_id", lambda: 9)

    resource = financial_resource.FinancialEntrySettlementListResource()
    with app.test_request_context(
        "/api/financial/entries/88/settlements?company_id=9",
        method="POST",
        json={"settlement_type": "manual", "principal_amount": 100},
    ):
        response, status = resource.post.__wrapped__(resource, 88)

    assert status == 409
    assert response["error"] == "Este lançamento está vinculado a um Título Financeiro. Faça a baixa pelo fluxo do título."
    assert response["redirect_url"].endswith("/financial/schedules/15?company_id=9&open_tab=baixas&entry_id=88")
