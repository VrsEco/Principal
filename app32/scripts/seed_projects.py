from app import app
import models
from datetime import datetime, timedelta

db = models.db
Company = models.Company
Project = models.Project

def seed_data():
    with app.app_context():
        # Models are already registered in MetaData via app import
        
        # Check if company exists
        company = Company.query.filter_by(client_code="VT001").first()
        if not company:
            company = Company(
                name="Versus Tech Demo",
                client_code="VT001",
                description="Empresa de tecnologia e consultoria.",
                segment="Tecnologia",
                size="Médio"
            )
            db.session.add(company)
            db.session.commit()
            print(f"✅ Company created: {company.name}")

        # Add some projects
        projects_data = [
            {
                "name": "Marketing Digital 2024",
                "notes": "Campanhas de aquisição para o novo SaaS.",
                "status": "in_progress",
                "owner": "Renato Santos",
                "progress": 45,
                "deadline": datetime.now() + timedelta(days=60)
            },
            {
                "name": "Expansão de Infraestrutura",
                "notes": "Upgrade dos clusters Kubernetes e migração para nova região.",
                "status": "planned",
                "owner": "Clara Mendes",
                "progress": 0,
                "deadline": datetime.now() + timedelta(days=120)
            },
            {
                "name": "Treinamento Interno",
                "notes": "Capacitação técnica para o time de suporte.",
                "status": "completed",
                "owner": "Fernando Lima",
                "progress": 100,
                "deadline": datetime.now() - timedelta(days=15)
            }
        ]

        for p_data in projects_data:
            existing = Project.query.filter_by(name=p_data['name']).first()
            if not existing:
                project = Project(
                    company_id=company.id,
                    name=p_data['name'],
                    notes=p_data['notes'],
                    status=p_data['status'],
                    owner=p_data['owner'],
                    progress=p_data['progress'],
                    deadline=p_data['deadline'].date()
                )
                db.session.add(project)
        
        db.session.commit()
        print("✅ Demo projects seeded successfully!")

if __name__ == "__main__":
    seed_data()
