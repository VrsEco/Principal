
from app import create_app
from models import db, Process
app = create_app()
with app.app_context():
    ids = db.session.query(Process.company_id).distinct().all()
    print(f"Distinct company IDs in processes: {ids}")
