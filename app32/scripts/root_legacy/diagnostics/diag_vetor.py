from app import create_app
from models import db, IncentiveRule, Indicator
import json

app = create_app()
with app.app_context():
    # Check columns
    print("Columns in incentive_rules:")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('incentive_rules')]
    print(columns)
    
    # Try dummy creation
    try:
        # Get a valid company, ruleset, and indicator
        from models import IncentiveRuleSet, Company
        rs = IncentiveRuleSet.query.first()
        ind = Indicator.query.first()
        if rs and ind:
            print(f"Testing with RuleSet ID {rs.id} and Indicator ID {ind.id}")
            v = IncentiveRule(
                company_id=rs.company_id,
                rule_set_id=rs.id,
                indicator_id=ind.id,
                vetor_type='multiplicador',
                ranges_config=[{'color': 'red', 'value': 0.5}],
                impact_value=1.5
            )
            db.session.add(v)
            db.session.commit()
            print("✅ Creation successful")
            db.session.delete(v)
            db.session.commit()
        else:
            print("❌ No RuleSet or Indicator found to test")
    except Exception as e:
        print(f"❌ Error: {e}")
