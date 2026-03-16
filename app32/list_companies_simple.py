from app import create_app
from models import Company, db

def list_companies():
    app = create_app()
    with app.app_context():
        companies = Company.query.all()
        for c in companies:
            print(f"ID: {c.id}, Name: {c.name}")

if __name__ == "__main__":
    list_companies()
