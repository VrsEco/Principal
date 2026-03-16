from flask import Blueprint, render_template, redirect, session, url_for
from sqlalchemy import text

from models import db
from utils.permissions import permission_required

indicators_bp = Blueprint('indicators', __name__)

@indicators_bp.route('/indicators')
@permission_required('indicators', 'view')
def indicators_list():
    """Unified Indicators list page"""
    from flask import session, redirect, url_for
    from models import Indicator
    company_id = session.get('active_company_id')
    if not company_id: return redirect(url_for('auth.portal'))
    
    indicators = Indicator.query.filter_by(company_id=int(company_id)).order_by(
        Indicator.source_module, Indicator.name
    ).all()
    # Using the more complete incentive template as the unified view
    return render_template('modules/incentives/indicator_list.html', indicators=indicators)

@indicators_bp.route('/indicators/<int:indicator_id>')
@permission_required('indicators', 'view')
def indicator_details(indicator_id):
    """Indicator details page (dashboard/history)"""
    return render_template('modules/indicators/indicator_details_v2.html', indicator_id=indicator_id)

@indicators_bp.route('/indicators/new')
@permission_required('indicators', 'create')
def indicator_new():
    """New indicator form"""
    return render_template('modules/indicators/indicator_form_v2.html')

@indicators_bp.route('/indicators/<int:indicator_id>/edit')
@permission_required('indicators', 'edit')
def indicator_edit(indicator_id):
    """Edit indicator form"""
    return render_template('modules/indicators/indicator_form_v2.html', indicator_id=indicator_id)

@indicators_bp.route('/indicators/analysis')
@permission_required('indicators', 'view')
def indicator_analysis():
    """Análise comparativa compatível com o schema atual de produção."""
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))

    cid = int(company_id)
    indicators_payload = []
    goals_payload = []
    data_payload = []

    try:
        indicators_payload = [
            dict(row._mapping)
            for row in db.session.execute(
                text(
                    """
                    SELECT
                        i.id,
                        i.code,
                        i.name,
                        i.indicator_type,
                        i.source_module,
                        i.unit,
                        i.polarity
                    FROM indicators i
                    WHERE i.company_id = :company_id
                      AND COALESCE(i.is_active, TRUE) = TRUE
                    ORDER BY i.source_module NULLS LAST, i.name
                    """
                ),
                {'company_id': cid}
            )
        ]

        goals_payload = [
            {
                **dict(row._mapping),
                'goal_value': float(row._mapping['goal_value']) if row._mapping.get('goal_value') is not None else None,
                'goal_date': row._mapping['goal_date'].isoformat() if row._mapping.get('goal_date') else None,
                'period_start': row._mapping['period_start'].isoformat() if row._mapping.get('period_start') else None,
                'period_end': row._mapping['period_end'].isoformat() if row._mapping.get('period_end') else None,
            }
            for row in db.session.execute(
                text(
                    """
                    SELECT
                        g.id,
                        g.indicator_id,
                        g.code,
                        g.goal_value,
                        g.goal_date,
                        g.period_start,
                        g.period_end,
                        g.status,
                        g.goal_type
                    FROM indicator_goals g
                    WHERE g.company_id = :company_id
                    ORDER BY g.goal_date DESC NULLS LAST, g.id DESC
                    """
                ),
                {'company_id': cid}
            )
        ]

        data_payload = [
            {
                'id': row._mapping['id'],
                'indicator_id': row._mapping['indicator_id'],
                'goal_id': row._mapping['goal_id'],
                'measured_value': float(row._mapping['measured_value']) if row._mapping.get('measured_value') is not None else None,
                'measured_date': row._mapping['measured_date'].isoformat() if row._mapping.get('measured_date') else None,
                'status': 'verified',
            }
            for row in db.session.execute(
                text(
                    """
                    SELECT
                        d.id,
                        g.indicator_id,
                        d.goal_id,
                        d.value AS measured_value,
                        d.record_date AS measured_date
                    FROM indicator_data d
                    JOIN indicator_goals g ON g.id = d.goal_id
                    WHERE d.company_id = :company_id
                      AND g.company_id = :company_id
                    ORDER BY d.record_date DESC, d.id DESC
                    """
                ),
                {'company_id': cid}
            )
        ]
    except Exception:
        indicators_payload = []
        goals_payload = []
        data_payload = []

    return render_template(
        'modules/indicators/comparative_analysis.html',
        indicators_payload=indicators_payload,
        goals_payload=goals_payload,
        data_payload=data_payload,
    )
