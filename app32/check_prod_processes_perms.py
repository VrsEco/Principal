import sys
sys.path.insert(0, '.')
from app import create_app
from models import Role
app = create_app()
with app.app_context():
    r = Role.query.all()
    count_with_view = sum(1 for role in r if role.permissions and 'view' in role.permissions.get('processes', []))
    print('PRODUCTION DB HAS', count_with_view, 'ROLES WITH VIEW PROCESS PERMISSION out of', len(r))
