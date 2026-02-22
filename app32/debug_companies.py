from app import create_app
from models import db, Company, ProcessArea, MacroProcess, Process

app = create_app()

def check_all_companies():
    with app.app_context():
        companies = Company.query.all()
        with open("debug_companies_output.txt", "w", encoding="utf-8") as f:
            f.write(f"{'ID':<5} | {'Name':<30} | {'Areas':<6} | {'Macros':<6} | {'Procs':<6}\n")
            f.write("-" * 65 + "\n")
            for c in companies:
                areas = ProcessArea.query.filter_by(company_id=c.id).count()
                macros = MacroProcess.query.filter_by(company_id=c.id).count()
                procs = Process.query.filter_by(company_id=c.id).count()
                f.write(f"{c.id:<5} | {c.name[:30]:<30} | {areas:<6} | {macros:<6} | {procs:<6}\n")

if __name__ == "__main__":
    check_all_companies()
