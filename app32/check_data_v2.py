from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT id, rule_set_id, indicator_id FROM incentive_rules"))
        print("DATA IN incentive_rules:")
        for row in result:
            # Check if this indicator exists in 'indicators'
            exists = conn.execute(text(f"SELECT 1 FROM indicators WHERE id={row.indicator_id}")).fetchone() is not None
            print(f"ID: {row.id}, RuleSet: {row.rule_set_id}, IndID: {row.indicator_id}, Exists in indicators? {exists}")
