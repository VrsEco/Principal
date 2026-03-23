from app import app
from models.company import Company
from models.project import Project

def find_projects():
    with app.app_context():
        # Search for the company
        search_term = 'AA - Versus Gestão Corporativa'
        company = Company.query.filter(
            (Company.name.ilike(f'%{search_term}%')) | 
            (Company.legal_name.ilike(f'%{search_term}%'))
        ).first()

        if not company:
            print(f"Empresa '{search_term}' não encontrada.")
            return

        print(f"Empresa encontrada: {company.name} (ID: {company.id})")

        # Search for open projects (planned or in_progress)
        projects = Project.query.filter(
            Project.company_id == company.id,
            Project.status.in_(['planned', 'in_progress'])
        ).all()

        if not projects:
            print(f"Não foram encontrados projetos abertos para a empresa {company.name}.")
        else:
            print(f"Projetos abertos ({len(projects)}):")
            for p in projects:
                print(f"- {p.name} (Status: {p.status}, Progresso: {p.progress}%)")

if __name__ == "__main__":
    find_projects()
