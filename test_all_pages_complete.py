#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste COMPLETO de todas as páginas
"""

import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'http://127.0.0.1:5002'

# Páginas para testar
pages = [
    ('/', 'Home'),
    ('/login', 'Login'),
    ('/main', 'Main Menu'),
    ('/companies', 'Empresas'),
    ('/pev/dashboard', 'PEV Dashboard'),
    ('/grv/dashboard', 'GRV Dashboard'),
    ('/configs', 'Configurações'),
    ('/settings/reports', 'Relatórios'),
    ('/integrations', 'Integrações'),
    ('/configs/ai', 'AI Config'),
]

print("=" * 80)
print("TESTE COMPLETO DE PÁGINAS - PostgreSQL")
print("=" * 80)

ok = 0
warn = 0
error = 0

for path, name in pages:
    try:
        r = requests.get(BASE_URL + path, timeout=5, allow_redirects=False)
        status = r.status_code
        
        if status == 200:
            print(f"  OK  [200] {name}")
            ok += 1
        elif status == 302:
            print(f"  OK  [302] {name} (redirect)")
            ok += 1
        elif status == 500:
            print(f" ERRO [500] {name}")
            error += 1
        else:
            print(f" WARN [{status}] {name}")
            warn += 1
            
    except Exception as e:
        print(f" ERRO [---] {name}: {e}")
        error += 1

print("\n" + "=" * 80)
print(f"RESUMO: {ok} OK | {warn} Avisos | {error} Erros")
print("=" * 80)

if error == 0:
    print("\n>> TODOS OS TESTES PASSARAM!")
    sys.exit(0)
else:
    print(f"\n>> {error} página(s) com erro")
    sys.exit(1)

