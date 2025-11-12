#!/usr/bin/env python3
"""
Teste final completo após correções
"""

import requests
import time

print("="*80)
print("TESTE FINAL - CORREÇÃO DE TIPOS DE PLANEJAMENTO")
print("="*80)

# Aguardar um momento para o servidor estar pronto
time.sleep(2)

# 1. Testar API
print("\n1. TESTANDO API...")
try:
    response = requests.get("http://127.0.0.1:5003/api/companies/13/projects", timeout=10)
    if response.status_code == 200:
        data = response.json()
        projects = data.get('projects', [])
        
        implantacao = [p for p in projects if p.get('plan_mode') == 'implantacao']
        evolucao = [p for p in projects if p.get('plan_mode') == 'evolucao']
        
        print(f"   ✅ API funcionando")
        print(f"   - Projetos de IMPLANTAÇÃO: {len(implantacao)}")
        print(f"   - Projetos de EVOLUÇÃO: {len(evolucao)}")
        
        # Detalhar projetos de implantação
        if implantacao:
            print(f"\n   Projetos de IMPLANTAÇÃO encontrados:")
            for p in implantacao:
                print(f"     • ID {p.get('id')}: {p.get('title', 'N/A')[:50]}")
                print(f"       Plan ID: {p.get('plan_id')}, Mode: {p.get('plan_mode')}")
                
                # Verificar qual link seria gerado
                plan_mode = (p.get('plan_mode') or 'evolucao').lower()
                if plan_mode == 'implantacao':
                    url = f"/pev/implantacao?plan_id={p.get('plan_id')}"
                    print(f"       Link: {url} ✅")
                else:
                    print(f"       ❌ ERRO: plan_mode não é implantacao!")
    else:
        print(f"   ❌ Erro HTTP {response.status_code}")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. Testar redirecionamento direto
print("\n2. TESTANDO REDIRECIONAMENTOS...")

urls_testar = [
    ("http://127.0.0.1:5003/plans/7", "/pev/implantacao?plan_id=7", "Implantação"),
    ("http://127.0.0.1:5003/plans/8", "/pev/implantacao?plan_id=8", "Implantação"),
    ("http://127.0.0.1:5003/plans/7/projects", "/pev/implantacao?plan_id=7", "Implantação"),
]

for url_origem, url_esperada, tipo in urls_testar:
    try:
        # allow_redirects=False para pegar o redirect
        response = requests.get(url_origem, allow_redirects=False, timeout=10)
        
        if response.status_code in [301, 302, 303, 307, 308]:
            location = response.headers.get('Location', '')
            if url_esperada in location:
                print(f"   ✅ {url_origem}")
                print(f"      Redireciona para: {location}")
            else:
                print(f"   ❌ {url_origem}")
                print(f"      Esperado: {url_esperada}")
                print(f"      Recebido: {location}")
        else:
            print(f"   ⚠️ {url_origem}")
            print(f"      Status: {response.status_code} (sem redirect)")
    except Exception as e:
        print(f"   ❌ Erro ao testar {url_origem}: {e}")

print("\n" + "="*80)
print("TESTE COMPLETO!")
print("="*80)
print("\nPróximos passos:")
print("1. Acesse http://127.0.0.1:5003/grv/company/13/projects/projects")
print("2. Clique em 'Abrir no planejamento' no projeto de implantação")
print("3. Verifique se vai para a interface de implantação")
print("="*80)























