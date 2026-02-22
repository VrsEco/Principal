import sys
import os
import json

# Padronizacao de caminho para raiz app32
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app
from flask import url_for

app = create_app()

def test_api():
    with app.test_client() as client:
        # We need a session with a logged in user, or bypass login
        # Since this is a check, let's just query the function logic or bypass auth
        print("--- TESTANDO API DE PORTFOLIOS ---")
        
        # Test direct logic of the search
        from models.portfolio import Portfolio
        cid = 36
        portfolios = Portfolio.query.filter_by(company_id=cid).all()
        print(f"No Banco (SQLAlchemy): {len(portfolios)} portfolios encontrados para empresa {cid}.")
        
        # Checking JSON serialization
        data = [p.to_dict(include_project_count=True) for p in portfolios]
        print(f"JSON Serializado: {json.dumps(data, indent=2)}")

if __name__ == "__main__":
    test_api()
