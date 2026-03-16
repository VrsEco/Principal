from app import create_app
from models import db, IncentiveRule
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('incentive_rules')]
    print("COLUMNS_START")
    print(",".join(columns))
    print("COLUMNS_END")
