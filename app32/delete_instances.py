from app import create_app
from models import db, ProcessInstance

app = create_app()
with app.app_context():
    try:
        num = ProcessInstance.query.delete()
        db.session.commit()
        print(f"Deleted {num} process instances.")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
