from app import app
from src.intelligence.tools import list_my_companies
from models.user import User
from flask_login import login_user

def test_tool():
    with app.app_context():
        # Simula usuário logado (Fabiano - admin geralmente id 1 ou similar)
        user = User.query.filter_by(email='contato@versusgestao.com.br').first()
        if not user:
             user = User.query.first()
             
        print(f"Testando com usuário: {user.name} (ID: {user.id})")
        
        # Simula o ambiente que a tool espera (current_user)
        # Note: flask_login current_user requires a request context or manual mocking
        from unittest.mock import MagicMock
        import flask_login
        
        # Mocking current_user
        original_current_user = flask_login.current_user
        flask_login.current_user = user
        
        try:
            result = list_my_companies.invoke({"search_term": "Versus"})
            print("Resultado da busca 'Versus':")
            print(result)
            
            result_aa = list_my_companies.invoke({"search_term": "AA"})
            print("\nResultado da busca 'AA':")
            print(result_aa)
        finally:
            flask_login.current_user = original_current_user

if __name__ == "__main__":
    test_tool()
