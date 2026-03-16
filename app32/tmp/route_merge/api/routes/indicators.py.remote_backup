from flask import Blueprint, render_template
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
