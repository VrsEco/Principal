
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models import db, ProjectTask

app = create_app()
with app.app_context():
    # Update Ondas 1-3
    target_ids = [267, 268, 269, 270]
    tasks = ProjectTask.query.filter(ProjectTask.id.in_(target_ids)).all()
    
    for t in tasks:
        print(f"Updating Task {t.id}: {t.what} -> completed")
        t.status = 'completed'
    
    # Add a final summary task
    new_task = ProjectTask(
        project_id=31,
        what='ENTREGA: Sistema de Incentivos Alinhados - Ondas 1A, 1B, 2 e 3 implementadas e em produção.',
        how='Deploy realizado em 2026-03-12. Camada de fatos, motor de cálculo, adaptadores e auditoria validados.',
        priority='high',
        stage='done',
        status='completed'
    )
    db.session.add(new_task)
    
    db.session.commit()
    print("SUCCESS: Project AA.J.31 updated in production.")
