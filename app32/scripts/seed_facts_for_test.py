from app import create_app
from models import User, Employee, IncentiveIndicator, IncentiveFact, db
from datetime import date
from decimal import Decimal

app = create_app()
with app.app_context():
    u = User.query.first()
    if not u:
        print("No user found.")
        exit()
        
    print(f"User: {u.name} (ID: {u.id})")
    
    emp = Employee.query.filter_by(user_id=u.id, company_id=9).first()
    if not emp:
        print("Employee not found for company 9. Creating one...")
        emp = Employee(user_id=u.id, company_id=9, name=u.name, status='active')
        db.session.add(emp)
        db.session.commit()
    
    print(f"Employee ID: {emp.id}")
    
    # Add some mock facts for company 9
    indicators = IncentiveIndicator.query.filter_by(company_id=9).all()
    for ind in indicators:
        fact = IncentiveFact.query.filter_by(
            indicator_id=ind.id,
            employee_id=emp.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31)
        ).first()
        
        if not fact:
            val = Decimal('110.00') if 'process' in (ind.source_module or '') else Decimal('95.00')
            fact = IncentiveFact(
                company_id=9,
                indicator_id=ind.id,
                employee_id=emp.id,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                value=val,
                status='verified'
            )
            db.session.add(fact)
    
    db.session.commit()
    print("Mock facts created for testing statement.")
