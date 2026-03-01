
from app import create_app
from models import db, AgentAction
import json

app = create_app('production')
with app.app_context():
    try:
        actions = AgentAction.query.order_by(AgentAction.id.desc()).limit(10).all()
        result = []
        for a in actions:
            result.append({
                'id': a.id,
                'type': a.type,
                'title': a.title,
                'status': a.status,
                'description': a.description,
                'payload': a.payload
            })
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
