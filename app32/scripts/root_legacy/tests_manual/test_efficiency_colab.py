import sys
import logging
from app import create_app
from models import db, User, Employee

app = create_app()

print("App created")

with app.app_context():
    colab_user = User.query.filter(User.role != 'admin', User.is_active == True).first()
    if not colab_user:
        print("Nenhum usuario colaborador encontrado.")
        sys.exit(0)
        
    print(f"Testando com user: {colab_user.email} (Role: {colab_user.role})")
    
    emp = Employee.query.filter_by(user_id=colab_user.id, status='active').first()
    if not emp:
        print("Nenhum empregado associado a este user encontrado.")
        sys.exit(0)
        
    company_id = emp.company_id
    print(f"Company ID: {company_id}, Employee ID: {emp.id}, Employee Name: {emp.name}")

    client = app.test_client()
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(colab_user.id)
            sess['_fresh'] = True
            sess['active_company_id'] = company_id

        # Simula request autenticado
        response = client.get(f'/api/companies/{company_id}/efficiency/collaborators')
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            if not isinstance(data, list):
                print("Erro: Resposta não é uma lista", data)
                sys.exit(1)
            
            print(f"Numero de colaboradores retornados: {len(data)}")
            for item in data:
                print(f" - {item.get('employee_name')}")
            
            other_names = [d['employee_name'] for d in data if d['employee_name'] != emp.name]
            if other_names:
                print(f"ERRO: Colaborador viu dados de outros: {other_names}")
                sys.exit(1)
            else:
                print("SUCESSO: Colaborador só viu seus próprios dados.")
                sys.exit(0)
        else:
            print("Falhou a requisição:", response.get_data(as_text=True))
            sys.exit(1)
