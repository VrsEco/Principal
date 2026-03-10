
import sys
sys.path.insert(0, r'c:\GestaoVersus\app32')

def update_project():
    from app import create_app
    from models import db, ProjectTask
    from datetime import datetime
    
    app = create_app('development')
    with app.app_context():
        # Create a task for today's mission
        new_task = ProjectTask(
            project_id=31,
            what="Fixing Production Dependencies: Implementação e Validação do Grafo de Dependências (Deploy Produção)",
            how="Identificação do 404, ajuste no passenger_wsgi, reset com Flask Migrate em servidor local + deploy validado",
            stage="completed",
            due_date=datetime.utcnow(),
            completion_date=datetime.utcnow()
        )
        db.session.add(new_task)
        db.session.commit()
        print(f"Task criada com sucesso: ID {new_task.id}")

if __name__ == '__main__':
    update_project()
