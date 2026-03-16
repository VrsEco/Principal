from app import create_app
from models import IncentiveRule, IncentiveRuleSet, IncentiveIndicator
app = create_app()
with app.app_context():
    cid = 9
    rs = IncentiveRuleSet.query.filter_by(company_id=cid).first()
    if rs:
        print(f"Found RuleSet: {rs.name} (ID: {rs.id})")
        rules = IncentiveRule.query.filter_by(rule_set_id=rs.id).all()
        print(f"Rules Count: {len(rules)}")
        for r in rules:
            ind = IncentiveIndicator.query.get(r.indicator_id)
            print(f"Rule: {r.id}, Ind: {ind.name if ind else 'UNK'}, Weight: {r.weight}, Target: {r.target_value}, Type: {r.impact_type}")
    else:
        print(f"No RuleSet for CID {cid}")
