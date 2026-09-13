from flask import Flask, session

from api.routes import portfolios as portfolios_route
from utils import permissions


def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    return app


def test_portfolio_routes_reject_foreign_company_before_database_access(monkeypatch):
    app = _app()
    monkeypatch.setattr(permissions, 'has_permission', lambda *_args: True)

    guarded_routes = (
        portfolios_route.list_portfolios,
        portfolios_route.create_portfolio,
        portfolios_route.get_portfolio,
        portfolios_route.portfolio_summary_options,
    )
    with app.test_request_context('/api/companies/22/portfolios'):
        session['active_company_id'] = 9
        for protected in guarded_routes:
            payload, status = protected(22, 7) if protected in guarded_routes[2:] else protected(22)
            assert status == 403
            assert 'não corresponde' in payload['error']


def test_portfolio_company_routes_bind_to_active_company_guard():
    guarded_routes = (
        portfolios_route.portfolios_page,
        portfolios_route.list_portfolios,
        portfolios_route.create_portfolio,
        portfolios_route.get_portfolio,
        portfolios_route.update_portfolio,
        portfolios_route.delete_portfolio,
        portfolios_route.portfolio_summary_options,
        portfolios_route.portfolio_summary_pdf,
        portfolios_route.send_portfolio_summary,
    )
    assert all(
        getattr(route, '_permission_required', {}).get('active_company_only') is True
        for route in guarded_routes
    )
