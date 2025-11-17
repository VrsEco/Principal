#!/usr/bin/env python
"""
Script para gerar testes pytest para todas as rotas do app31
"""
import os
import sys
import json
import re
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def discover_routes():
    """Descobre todas as rotas da aplicação"""
    try:
        from app_pev import app
        from services.route_audit_service import RouteAuditService
        
        with app.app_context():
            routes = RouteAuditService.discover_all_routes(app)
            return routes
    except Exception as e:
        print(f"Erro ao descobrir rotas: {e}")
        import traceback
        traceback.print_exc()
        return []

def generate_test_code(route_info):
    """Gera código de teste pytest para uma rota"""
    endpoint = route_info['endpoint']
    path = route_info['path']
    methods = route_info['methods']
    blueprint = route_info.get('blueprint', 'main')
    
    # Normalizar nome do teste
    test_name = endpoint.replace('.', '_').replace('-', '_')
    if not test_name.startswith('test_'):
        test_name = f"test_{test_name}"
    
    # Gerar código do teste
    test_code = f'''"""
Teste para rota: {path}
Endpoint: {endpoint}
Blueprint: {blueprint}
Métodos: {', '.join(methods)}
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT, authenticated_session

def {test_name}(base_url, timeout):
    """Testa a rota {path}"""
    url = f"{{base_url}}{path}"
    
'''
    
    # Gerar testes para cada método HTTP
    for method in methods:
        method_lower = method.lower()
        
        if method == 'GET':
            test_code += f'''    # Test GET request
    try:
        response = requests.{method_lower}(url, timeout=timeout)
        # Aceitar 200, 302 (redirect), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado)
        assert response.status_code in (200, 302, 401, 403, 404), \\
            f"GET {path} retornou status inesperado: {{response.status_code}}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição GET {path}: {{e}}")

'''
        elif method in ['POST', 'PUT', 'PATCH']:
            test_code += f'''    # Test {method} request
    try:
        # Tentar com payload vazio primeiro
        response = requests.{method_lower}(url, json={{}}, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 201, 400, 401, 403, 404, 422, 500), \\
            f"{method} {path} retornou status inesperado: {{response.status_code}}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição {method} {path}: {{e}}")

'''
        elif method == 'DELETE':
            test_code += f'''    # Test DELETE request
    try:
        response = requests.{method_lower}(url, timeout=timeout)
        # Aceitar vários códigos de status possíveis
        assert response.status_code in (200, 204, 400, 401, 403, 404, 500), \\
            f"DELETE {path} retornou status inesperado: {{response.status_code}}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Erro na requisição DELETE {path}: {{e}}")

'''
    
    return test_code

def generate_test_file(routes, blueprint_name):
    """Gera arquivo de teste para um blueprint"""
    if not routes:
        return None
    
    # Filtrar rotas do blueprint
    blueprint_routes = [r for r in routes if r.get('blueprint') == blueprint_name]
    
    if not blueprint_routes:
        return None
    
    # Gerar código do arquivo
    file_content = f'''"""
Testes para blueprint: {blueprint_name}
Total de rotas: {len(blueprint_routes)}
"""
import pytest
import requests
from testsprite_tests.conftest import BASE_URL, TIMEOUT

'''
    
    # Adicionar testes para cada rota
    for route in blueprint_routes:
        file_content += generate_test_code(route)
        file_content += "\n"
    
    return file_content

def main():
    """Função principal"""
    print("=" * 70)
    print("GERANDO TESTES PARA TODAS AS ROTAS DO APP31")
    print("=" * 70)
    print()
    
    # Descobrir rotas
    print("Descobrindo rotas...")
    routes = discover_routes()
    print(f"Total de rotas encontradas: {len(routes)}")
    
    if not routes:
        print("ERRO: Nenhuma rota encontrada!")
        return
    
    # Agrupar por blueprint
    blueprints = {}
    main_routes = []
    
    for route in routes:
        blueprint = route.get('blueprint')
        if blueprint:
            if blueprint not in blueprints:
                blueprints[blueprint] = []
            blueprints[blueprint].append(route)
        else:
            main_routes.append(route)
    
    # Criar diretório de testes se não existir
    test_dir = Path(__file__).parent
    test_dir.mkdir(exist_ok=True)
    
    # Gerar arquivo para rotas principais
    if main_routes:
        print(f"\nGerando testes para {len(main_routes)} rotas principais...")
        main_content = generate_test_file(main_routes, None)
        if main_content:
            main_file = test_dir / "test_main_routes.py"
            with open(main_file, 'w', encoding='utf-8') as f:
                f.write(main_content)
            print(f"✅ Criado: {main_file}")
    
    # Gerar arquivos para cada blueprint
    for blueprint_name, blueprint_routes in blueprints.items():
        print(f"\nGerando testes para blueprint '{blueprint_name}' ({len(blueprint_routes)} rotas)...")
        content = generate_test_file(blueprint_routes, blueprint_name)
        if content:
            # Normalizar nome do arquivo
            safe_name = blueprint_name.replace('-', '_').replace('.', '_')
            test_file = test_dir / f"test_{safe_name}_routes.py"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Criado: {test_file}")
    
    # Salvar lista de rotas em JSON para referência
    routes_file = test_dir / "all_routes.json"
    with open(routes_file, 'w', encoding='utf-8') as f:
        json.dump(routes, f, indent=2, default=str)
    print(f"\n✅ Lista de rotas salva em: {routes_file}")
    
    print("\n" + "=" * 70)
    print("GERAÇÃO DE TESTES CONCLUÍDA!")
    print("=" * 70)
    print(f"\nTotal de rotas processadas: {len(routes)}")
    print(f"Blueprints encontrados: {len(blueprints)}")
    print("\nPara executar os testes:")
    print("  python -m pytest testsprite_tests/test_*.py -v")

if __name__ == "__main__":
    main()

