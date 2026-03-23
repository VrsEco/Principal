from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    result = db.session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    print(f"Current DB Version: {result[0] if result else 'None'}")

    # Check heads
    from flask_migrate import heads
    print(f"Heads: {heads}")
