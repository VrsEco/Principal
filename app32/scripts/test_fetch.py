from app import create_app
from api.resources.process import fetch_pop_routines
import json

app = create_app()
with app.app_context():
    routines = fetch_pop_routines(171)
    print(f"Routines for 171: {json.dumps(routines, indent=2)}")
