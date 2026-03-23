from app import create_app
from models import db, Company
import traceback

app = create_app()
with app.app_context():
    try:
        print("Checking Company mapper...")
        from sqlalchemy import inspect
        mapper = inspect(Company)
        print(f"Attributes: {list(mapper.attrs.keys())}")
        if 'plans' in mapper.attrs:
            print("✅ 'plans' relationship found!")
        else:
            print("❌ 'plans' relationship MISSING!")
            
        # Try to trigger the Marshmallow error
        print("\nChecking CompanySchema...")
        from schemas.company import company_schema
        print("✅ CompanySchema initialized!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
