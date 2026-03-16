from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT id, indicator_id FROM incentive_rules"))
        print("DATA IN incentive_rules:")
        for row in result:
            print(f"ID: {row.id}, Indicator ID: {row.indicator_id}")
            
        result = conn.execute(text("SELECT id FROM indicators WHERE id IN (SELECT indicator_id FROM incentive_rules)"))
        print("\nCorresponding entries in 'indicators':")
        for row in result:
            print(f"Found ID: {row.id}")
