from app import app
from models.project import Project

def list_projects_id5():
    with app.app_context():
        projects = Project.query.filter_by(company_id=5).all()
        print(f"Total de projetos para ID 5: {len(projects)}")
        for p in projects:
            print(f"- ID: {p.id} | Nome: {p.name} | Status: {p.status}")

if __name__ == "__main__":
    list_projects_id5()
