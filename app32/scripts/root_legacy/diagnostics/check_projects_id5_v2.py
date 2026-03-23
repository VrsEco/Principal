from app import app
from models.project import Project

def list_projects_id5():
    output_path = "projects_id5_data.txt"
    with app.app_context():
        projects = Project.query.filter_by(company_id=5).all()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Total de projetos para ID 5: {len(projects)}\n")
            for p in projects:
                f.write(f"- ID: {p.id} | Nome: {p.name} | Status: {p.status} | Progresso: {p.progress}%\n")
    print(f"Output written to {output_path}")

if __name__ == "__main__":
    list_projects_id5()
