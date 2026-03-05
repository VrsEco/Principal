
import sys
import os
sys.path.append(os.getcwd())
try:
    from app import create_app
    from models import db
    app = create_app()
    with app.app_context():
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        print("MAPPERS CONFIGURED SUCCESSFULLY")
except Exception as e:
    import traceback
    traceback.print_exc()
