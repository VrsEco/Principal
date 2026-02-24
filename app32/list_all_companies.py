from app import app
from models.company import Company

def list_companies():
    with app.app_context():
        companies = Company.query.all()
        print(f"Total de empresas: {len(companies)}")
        for c in companies:
            print(f"ID: {c.id} | Nome: {c.name} | Razão Social: {c.legal_name}")

if __name__ == "__main__":
    list_companies()
