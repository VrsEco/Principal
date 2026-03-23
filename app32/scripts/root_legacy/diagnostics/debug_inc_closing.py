from app import create_app
from models import IncentiveCalculation, Company, db
from flask import session

def debug_closing_route():
    app = create_app()
    with app.app_context():
        # Check all calculations for company 9
        cid = 9
        calcs = IncentiveCalculation.query.filter_by(company_id=cid).all()
        print(f"Calculations for company {cid}:")
        for c in calcs:
            print(f"ID: {c.id}, Period: {c.period_start} to {c.period_end}, Status: {c.status}")
            
        # Check the latest one
        last = IncentiveCalculation.query.filter_by(company_id=cid).order_by(IncentiveCalculation.id.desc()).first()
        if last:
            print(f"\nLast Calc Result Payload Type: {type(last.results_payload)}")
            if last.results_payload:
                print(f"Participants count in payload: {len(last.results_payload.get('participants', []))}")
            else:
                print("WARNING: results_payload is NULL")
        else:
            print("\nNo calculations found for company 9")

if __name__ == "__main__":
    debug_closing_route()
