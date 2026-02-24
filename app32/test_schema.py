from app import create_app
from models import db, Company
from schemas.company import company_schema

app = create_app()
with app.app_context():
    c = Company.query.get(4)
    print(c)
    try:
        data = {"name": c.name, "client_code": c.client_code}
        res = company_schema.load(data, instance=c, partial=True)
        print("Success:", res)
    except Exception as e:
        print("Error:", e)
