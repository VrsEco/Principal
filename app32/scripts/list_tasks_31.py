
import sys
sys.path.insert(0, r'c:\GestaoVersus\app32')

def run():
    from app import create_app
    from models import db, ProjectTask
    
    app = create_app('development')
    with app.app_context():
        tasks = ProjectTask.query.filter_by(project_id=31).all()
        for t in tasks:
            print(f"Task ID: {t.id} | Stage: {t.stage} | What: {t.what}")

if __name__ == '__main__':
    run()
