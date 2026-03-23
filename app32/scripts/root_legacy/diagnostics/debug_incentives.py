from app import create_app
from models import IncentiveRuleSet, Company, Employee, User
import json

app = create_app()
with app.app_context():
    data = {
        "rule_sets": [{"id": rs.id, "name": rs.name, "company_id": rs.company_id} for rs in IncentiveRuleSet.query.all()],
        "companies": [{"id": c.id, "name": c.name} for c in Company.query.all()],
        "incentive_rule_sets_count": IncentiveRuleSet.query.count()
    }
    with open('debug_results.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Done")
