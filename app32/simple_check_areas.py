
import sys
import os

# Create a minimal mock app to get the context if needed, or just import models
project_root = r"c:\GestaoVersus\app32"
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app
from models import db, ProcessArea

app = create_app()
with app.app_context():
    try:
        company_id = 5
        areas = ProcessArea.query.filter_by(company_id=company_id).all()
        print(f"AREAS_COUNT:{len(areas)}")
        for a in areas:
            print(f"AREA_ID:{a.id}|NAME:{a.name}")
    except Exception as e:
        print(f"ERROR:{e}")
        import traceback
        traceback.print_exc()
