#!/usr/bin/env python3
"""
Criar portfólio de teste com projetos associados
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5002"
COMPANY_ID = 14

def create_test_portfolio_with_projects():
    """Cria um portfólio de teste com projetos associados."""
    
    print("Criando portfólio de teste com projetos...")
    
    # 1. Criar portfólio
    print("1. Criando portfólio...")
    portfolio_data = {
        "code": "TEST_VALIDATION",
        "name": "Portfólio Teste Validação",
        "responsible_id": None,
        "notes": "Para teste de validação de exclusão"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/companies/{COMPANY_ID}/portfolios",
            json=portfolio_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            data = response.json()
            portfolio_id = data.get('portfolio', {}).get('id')
            print(f"   Portfólio criado com ID: {portfolio_id}")
        else:
            print(f"   Erro ao criar portfólio: {response.text}")
            return None
    except Exception as e:
        print(f"   Exceção ao criar portfólio: {e}")
        return None
    
    # 2. Criar projeto associado ao portfólio
    print("2. Criando projeto associado...")
    project_data = {
        "title": "Projeto de Teste",
        "description": "Projeto para teste de validação",
        "plan_id": portfolio_id,
        "plan_type": "GRV",
        "status": "active",
        "priority": "medium",
        "owner": "Teste"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/companies/{COMPANY_ID}/projects",
            json=project_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            data = response.json()
            project_id = data.get('project', {}).get('id')
            print(f"   Projeto criado com ID: {project_id}")
        else:
            print(f"   Erro ao criar projeto: {response.text}")
            print("   Continuando com o teste mesmo assim...")
    except Exception as e:
        print(f"   Exceção ao criar projeto: {e}")
        print("   Continuando com o teste mesmo assim...")
    
    return portfolio_id

def test_portfolio_with_projects():
    """Testa portfólio com projetos."""
    
    portfolio_id = create_test_portfolio_with_projects()
    if not portfolio_id:
        print("Não foi possível criar portfólio para teste")
        return
    
    print(f"\n3. Testando exclusão do portfólio ID {portfolio_id}...")
    
    # Verificar se há projetos associados
    try:
        response = requests.get(f"{BASE_URL}/api/companies/{COMPANY_ID}/portfolios")
        if response.status_code == 200:
            data = response.json()
            portfolios = data.get('portfolios', [])
            
            test_portfolio = None
            for p in portfolios:
                if p['id'] == portfolio_id:
                    test_portfolio = p
                    break
            
            if test_portfolio:
                project_count = test_portfolio.get('project_count', 0)
                print(f"   Portfólio encontrado: {test_portfolio['name']}")
                print(f"   Projetos associados: {project_count}")
            else:
                print("   Portfólio não encontrado na listagem")
                project_count = 0
        else:
            print("   Erro ao listar portfólios")
            project_count = 0
    except Exception as e:
        print(f"   Exceção ao listar: {e}")
        project_count = 0
    
    # Tentar excluir
    print(f"\n4. Tentando excluir portfólio ID {portfolio_id}...")
    try:
        response = requests.delete(f"{BASE_URL}/api/companies/{COMPANY_ID}/portfolios/{portfolio_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.text}")
        
        if project_count > 0:
            if response.status_code == 409:
                print("   SUCESSO: Portfólio não foi excluído (validação funcionou)")
            else:
                print("   ERRO: Portfólio foi excluído quando não deveria ter sido")
        else:
            if response.status_code == 200:
                print("   SUCESSO: Portfólio foi excluído (não tinha projetos)")
            else:
                print("   ERRO: Portfólio não foi excluído quando deveria ter sido")
    except Exception as e:
        print(f"   Exceção: {e}")

if __name__ == "__main__":
    test_portfolio_with_projects()

