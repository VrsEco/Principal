from app import app
from models.company import Company

def list_companies_codes():
    output_path = "companies_codes.txt"
    with app.app_context():
        companies = Company.query.all()
        with open(output_path, "w", encoding="utf-8") as f:
            for c in companies:
                f.write(f"ID: {c.id} | Code: {c.client_code} | Name: {c.name}\n")
    print(f"Output written to {output_path}")

if __name__ == "__main__":
    list_companies_codes()
