#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar se o servidor tem o blueprint de auditoria carregado
"""

import requests
import json

print("=" * 60)
print("VERIFICANDO SERVIDOR")
print("=" * 60)

# Testar se o servidor esta respondendo
print("\n[1] Testando servidor...")
try:
    response = requests.get('http://localhost:5002/', timeout=5)
    print(f"   [OK] Servidor respondendo: Status {response.status_code}")
except requests.exceptions.ConnectionError:
    print("   [ERRO] Servidor NAO esta rodando!")
    print("   Execute: python app_pev.py")
    exit(1)
except Exception as e:
    print(f"   [ERRO] {e}")
    exit(1)

# Testar rota de auditoria
print("\n[2] Testando rota /route-audit/...")
try:
    response = requests.get('http://localhost:5002/route-audit/', timeout=5, allow_redirects=False)
    
    if response.status_code == 404:
        print("   [ERRO] Rota /route-audit/ retornou 404!")
        print("   O blueprint NAO foi carregado.")
        print("   SOLUCAO: REINICIE a aplicacao:")
        print("   1. Pare o servidor (Ctrl+C)")
        print("   2. Execute: python app_pev.py")
        print("   3. Verifique a mensagem:")
        print("      'Sistema de auditoria de rotas integrado com sucesso!'")
    elif response.status_code == 302 or response.status_code == 401:
        print("   [OK] Rota existe! (redirecionando para login)")
        print("   Blueprint carregado com sucesso!")
    elif response.status_code == 200:
        print("   [OK] Rota acessivel!")
        print("   Blueprint carregado com sucesso!")
    else:
        print(f"   Status: {response.status_code}")
        
except Exception as e:
    print(f"   [ERRO] {e}")

# Testar rota de logs
print("\n[3] Testando rota /logs/...")
try:
    response = requests.get('http://localhost:5002/logs/', timeout=5, allow_redirects=False)
    
    if response.status_code == 404:
        print("   [ERRO] Rota /logs/ retornou 404!")
    elif response.status_code == 302 or response.status_code == 401:
        print("   [OK] Rota existe! (redirecionando para login)")
    elif response.status_code == 200:
        print("   [OK] Rota acessivel!")
    else:
        print(f"   Status: {response.status_code}")
        
except Exception as e:
    print(f"   [ERRO] {e}")

# Testar rota de login
print("\n[4] Testando rota /auth/login...")
try:
    response = requests.get('http://localhost:5002/auth/login', timeout=5)
    
    if response.status_code == 200:
        print("   [OK] Pagina de login acessivel!")
    else:
        print(f"   Status: {response.status_code}")
        
except Exception as e:
    print(f"   [ERRO] {e}")

print("\n" + "=" * 60)
print("VERIFICACAO CONCLUIDA")
print("=" * 60)

