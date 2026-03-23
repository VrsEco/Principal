
from app import create_app
from models import Process, Company
app = create_app()
with app.app_context():
    c1 = Company.query.get(1)
    if c1:
        count = Process.query.filter_by(company_id=1).count()
        print(f"Company 1 ({c1.name}): {count} processes")
    else:
        print("Company 1 not found")
