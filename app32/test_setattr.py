from app import create_app
from models import db, Company

app = create_app()
with app.app_context():
    company = Company.query.get(4)
    print("Before:", company.is_active, company.logo_primary)
    data = {
        "is_active": False,
        "logo_primary": "https://test.com/logo.png",
        "name": company.name,
        "client_code": "TEST8"
    }
    for key, value in data.items():
        if hasattr(company, key):
            setattr(company, key, value)
            print(f"Set {key} = {value}")
        else:
            print(f"Skipped {key}")
    db.session.commit()
    company2 = Company.query.get(4)
    print("After:", company2.is_active, company2.logo_primary, company2.client_code)
