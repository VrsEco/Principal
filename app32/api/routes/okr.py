from flask import Blueprint, render_template
from flask_login import login_required

okr_bp = Blueprint('okrs', __name__)

@okr_bp.route('/okrs')
@login_required
def okrs_list():
    """OKRs dashboard page"""
    return render_template('modules/okrs/okrs_v2.html')

@okr_bp.route('/okrs/new')
@login_required
def okr_create():
    """OKR creation page"""
    return render_template('modules/okrs/okr_form_v2.html')
