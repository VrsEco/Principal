from app import create_app
from services.incentive_service import IncentiveService
from models import IncentiveRuleSet, db
from datetime import date

app = create_app()
with app.app_context():
    cid = 9 # Versus
    rs = IncentiveRuleSet.query.filter_by(company_id=cid).first()
    if rs:
        print(f"Running simulation for RuleSet: {rs.name}")
        # Harvest first
        IncentiveService.harvest_all_modules(cid, date(2026, 1, 1), date(2026, 1, 31))
        res = IncentiveService.calculate_incentive(cid, rs.id, date(2026, 1, 1), date(2026, 1, 31))
        print(f"Result: {res['total_payout']} distributed among {len(res['participants'])} participants.")
    else:
        print("No RuleSet found for company 9.")
