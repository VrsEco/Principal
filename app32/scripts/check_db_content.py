from app import app
from models import Company, Indicator, IndicatorGroup, IndicatorGoal, IndicatorData

with app.app_context():
    companies = Company.query.all()
    print("COMPANIES:")
    for c in companies:
        print(f"ID: {c.id}, Name: {c.name}")
    
    indicators = Indicator.query.all()
    print("\nINDICATORS:")
    for i in indicators:
        print(f"ID: {i.id}, Code: {i.code}, Name: {i.name}")
