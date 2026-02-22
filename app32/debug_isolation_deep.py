from app import create_app
from models import User, Company, ProcessArea, MacroProcess, Process
from flask import session

app = create_app()

def test_isolation_deep():
    with app.app_context():
        all_companies = Company.query.all()
        print(f"Checking {len(all_companies)} companies...")
        
        for c in all_companies:
            print(f"\nProcessing Company: {c.name} (ID: {c.id})")
            
            # Check Areas in DB
            areas_db = ProcessArea.query.filter_by(company_id=c.id).all()
            print(f"  - DB Areas: {len(areas_db)}")
            for a in areas_db[:2]:
                print(f"    - Area: {a.name} (Code: {a.code})")

            # Check if Company 1 data exists for this ID (should be 0 unless it IS Company 1)
            # Actually, I want to check if the query for Company C.ID ever returns Area ID 1 (AO.C.1)
            cross_check = ProcessArea.query.filter_by(company_id=c.id).filter(ProcessArea.id == 1).first()
            if cross_check:
                print(f"  - WARNING: Query for Company {c.id} returned Area ID 1!")
            else:
                print(f"  - OK: Isolation at DB level for Area ID 1")

        # Now test via API Resource logic directly (simulating the resource code)
        from api.resources.process import ProcessAreaListResource
        from flask import request
        
        print("\nTesting API Logic via Resource Call")
        for cID in [5, 14, 13]:
            with app.test_request_context(f'/api/process-areas?company_id={cID}'):
                resource = ProcessAreaListResource()
                # Simulate the logic in GET but without the decorator to avoid auth issues in this script
                # (I'll just copy the logic here)
                query = ProcessArea.query.filter_by(company_id=cID)
                results = query.all()
                print(f"API result for Company {cID}: {len(results)} areas")
                if any(r.id == 1 for r in results):
                    print(f"  - BUG: Result includes Area ID 1!")
                else:
                    print(f"  - OK: No Area ID 1 in results")

if __name__ == "__main__":
    test_isolation_deep()
