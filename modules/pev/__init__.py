from flask import Blueprint, render_template
from datetime import datetime
from config_database import get_db

pev_bp = Blueprint('pev', __name__, url_prefix='/pev')


@pev_bp.route('/dashboard')
def pev_dashboard():
    # Dedicated PEV dashboard (was redirecting to core dashboard)
    db = get_db()
    companies = db.get_companies()

    companies_with_plans = []
    for company in companies:
        plans = db.get_plans_by_company(company['id'])
        company_with_plans = company.copy()
        company_with_plans['plans'] = [
            {'id': plan['id'], 'name': plan['name']}
            for plan in plans
        ]
        companies_with_plans.append(company_with_plans)

    highlights = [
        {"title": "Planejamentos Ativos", "value": "3", "trend": "+1"},
        {"title": "Participantes", "value": "15", "trend": "+3"},
        {"title": "Projetos em Andamento", "value": "8", "trend": "+2"}
    ]

    timeline = [
        {"date": "2025-01-15", "event": "Início do planejamento estratégico", "status": "completed"},
        {"date": "2025-02-01", "event": "Entrevistas com participantes", "status": "in_progress"},
        {"date": "2025-03-15", "event": "Definição de direcionadores", "status": "pending"},
        {"date": "2025-04-30", "event": "Aprovação final do plano", "status": "pending"}
    ]

    return render_template(
        "plan_selector.html",
        user_name="Fabiano Ferreira",
        companies=companies_with_plans,
        highlights=highlights,
        timeline=timeline
    )


