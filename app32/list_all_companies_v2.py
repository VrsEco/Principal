import os
from app import app
from models.company import Company

def list_companies():
    output_path = "companies_data.txt"
    with app.app_context():
        companies = Company.query.all()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Total de empresas: {len(companies)}\n")
            for c in companies:
                f.write(f"ID: {c.id} | Nome: {c.name} | Razão Social: {c.legal_name}\n")
    print(f"Output written to {output_path}")

if __name__ == "__main__":
    list_companies()
