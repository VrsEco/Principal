from app import app, db
from models import Indicator, IndicatorGroup, IndicatorGoal, IndicatorData

with app.app_context():
    # This will create tables in app32.db if they don't exist
    db.create_all()
    print("Tables created (if missing).")
    
    # Check if we can query them
    try:
        Indicator.query.first()
        IndicatorGroup.query.first()
        IndicatorGoal.query.first()
        IndicatorData.query.first()
        print("Indicator tables verified in Database (PostgreSQL)!")
    except Exception as e:
        print(f"Error: {e}")
