import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models.user import User

with app.app_context():
    from flask import url_for
    
    with app.test_client() as client:
        admin = User.query.filter_by(role='admin').first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True
        
        response = client.get('/my-work/api/activities?scope=me')
        data = response.get_json()
        
        print(f"Sucesso: {data.get('success')}")
        print(f"Total de Atividades no Array: {len(data.get('data', []))}")
        print(f"Stats Recebidos: {data.get('stats')}")
        
        # Testar filter options
        opts_response = client.get('/my-work/api/filter-options')
        opts = opts_response.get_json()
        print(f"Opcoes de Filtro Status: {opts.get('success')}")
        filters_data = opts.get('data', {})
        print(f"Total Empresas Filtro: {len(filters_data.get('companies', []))}")
        print(f"Total Colaboradores Filtro: {len(filters_data.get('collaborators', []))}")
        print(f"Total Projetos Filtro: {len(filters_data.get('projects', []))}")
