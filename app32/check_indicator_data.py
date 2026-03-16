from app import create_app
from models import db, IndicatorData
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Checking IndicatorData columns...")
    res = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'indicator_data'")).fetchall()
    columns = [r[0] for r in res]
    print(f"Columns in DB: {columns}")
    
    print("\nChecking if 'status' exists in IndicatorData object...")
    try:
        sample = IndicatorData.query.first()
        if sample:
            print(f"Sample data status: {getattr(sample, 'status', 'Attribute not found')}")
        else:
            print("No data in IndicatorData table.")
    except Exception as e:
        print(f"Error checking status: {e}")
