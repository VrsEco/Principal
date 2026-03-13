from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from services.incentive_service import IncentiveService
from models import Company, IncentiveRuleSet, Employee

incentives_bp = Blueprint('incentives', __name__, template_folder='templates')

@incentives_bp.route('/incentives')
@login_required
def dashboard():
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))
    
    company = Company.query.get(company_id)
    rule_sets = IncentiveRuleSet.query.filter_by(company_id=company_id).all()
    
    # Dynamic Stats
    from models import IncentiveIndicator, IncentiveCalculation, db
    from sqlalchemy import func
    
    indicators_count = IncentiveIndicator.query.filter_by(company_id=company_id, is_active=True).count()
    
    # Get last calculation totals
    last_calc = IncentiveCalculation.query.filter_by(company_id=company_id).order_by(IncentiveCalculation.created_at.desc()).first()
    
    # Historical Summary (Last 6 calculations)
    history = IncentiveCalculation.query.filter_by(company_id=company_id).order_by(IncentiveCalculation.created_at.desc()).limit(6).all()
    
    return render_template(
        'modules/incentives/dashboard.html',
        company=company,
        rule_sets=rule_sets,
        stats={
            "indicators": indicators_count,
            "total_payout": last_calc.total_distributed if last_calc else 0,
            "participants": last_calc.participants_count if last_calc else 0,
            "last_closing": last_calc.period_end if last_calc else None
        },
        history=history
    )

@incentives_bp.route('/incentives/spider-web')
@login_required
def spider_web():
    company_id = session.get('active_company_id')
    if not company_id:
        return redirect(url_for('auth.portal'))
        
    return render_template('modules/incentives/spider_web.html')

@incentives_bp.route('/incentives/rules/<int:rule_set_id>')
@login_required
def manage_rules(rule_set_id):
    company_id = session.get('active_company_id')
    rule_set = IncentiveRuleSet.query.get_or_404(rule_set_id)
    
    if rule_set.company_id != company_id:
        flash("Acesso negado.", "danger")
        return redirect(url_for('incentives.dashboard'))
        
    return render_template('modules/incentives/rules_manage.html', rule_set=rule_set)
