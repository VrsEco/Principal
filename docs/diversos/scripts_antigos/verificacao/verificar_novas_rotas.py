#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar se as novas rotas estao disponiveis
"""

import sys

print("=" * 60)
print("VERIFICANDO NOVAS ROTAS")
print("=" * 60)

# Testar imports
print("\n[1] Testando imports...")
try:
    from app_pev import app
    print("   [OK] app_pev importado")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

# Verificar rotas
print("\n[2] Verificando rotas registradas...")
try:
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    
    # Rotas que devem existir
    required_routes = [
        '/configs',
        '/configs/system',
        '/configs/system/audit'
    ]
    
    for route in required_routes:
        if route in routes:
            print(f"   [OK] {route}")
        else:
            print(f"   [ERRO] {route} - NAO ENCONTRADA")
    
    # Contar rotas configs
    config_routes = [r for r in routes if r.startswith('/configs')]
    print(f"\n   Total de rotas /configs/*: {len(config_routes)}")
    
except Exception as e:
    print(f"   [ERRO] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("VERIFICACAO CONCLUIDA")
print("=" * 60)

print("\nSe as rotas NAO foram encontradas:")
print("  1. REINICIE o servidor: python app_pev.py")
print("  2. Verifique mensagens de erro no console")
print("  3. Tente acessar novamente")

