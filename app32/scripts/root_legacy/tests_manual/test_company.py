from app import create_app
from models import db, Company

app = create_app()
with app.app_context():
    c = Company.query.get(4)
    print(f"Company 4: {c}")
    if c:
        print(f"Current is_active: {c.is_active}")
        print(f"Current logo_primary: {c.logo_primary}")
    else:
        print("Company 4 not found.")
