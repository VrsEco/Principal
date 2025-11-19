#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o sistema de logs automaticos
"""

import sys
import os

print("=" * 60)
print("TESTE DO SISTEMA DE LOGS AUTOMATICOS")
print("=" * 60)

# 1. Verificar imports
print("\n[1] Testando imports...")
try:
    from middleware.auto_log_decorator import auto_log_crud, get_auto_logging_config
    print("   [OK] middleware.auto_log_decorator")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

try:
    from services.route_audit_service import route_audit_service
    print("   [OK] services.route_audit_service")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

try:
    from api.route_audit import route_audit_bp
    print("   [OK] api.route_audit")
except Exception as e:
    print(f"   [ERRO] {e}")
    sys.exit(1)

# 2. Verificar arquivos
print("\n[2] Verificando arquivos...")
files_to_check = [
    'middleware/auto_log_decorator.py',
    'services/route_audit_service.py',
    'api/route_audit.py',
    'templates/route_audit/dashboard.html'
]

for file in files_to_check:
    if os.path.exists(file):
        print(f"   [OK] {file}")
    else:
        print(f"   [ERRO] {file} - NAO ENCONTRADO")

# 3. Verificar blueprint
print("\n[3] Testando blueprint...")
try:
    print(f"   Blueprint name: {route_audit_bp.name}")
    print(f"   URL prefix: {route_audit_bp.url_prefix}")
    
    # Contar rotas do blueprint
    route_count = len([r for r in route_audit_bp.deferred_functions])
    print(f"   [OK] {route_count} rotas registradas")
except Exception as e:
    print(f"   [ERRO] {e}")

# 4. Verificar configuracao
print("\n[4] Testando configuracao...")
try:
    config = get_auto_logging_config()
    print(f"   [OK] Entidades habilitadas: {len(config['enabled_entities'])}")
    print(f"   [OK] Entidades desabilitadas: {len(config['disabled_entities'])}")
    print(f"   [OK] Padroes de URL: {len(config['entity_patterns'])}")
except Exception as e:
    print(f"   [ERRO] {e}")

# 5. Testar app
print("\n[5] Testando integracao com app...")
try:
    from app_pev import app
    
    # Verificar se blueprint esta registrado
    blueprints = list(app.blueprints.keys())
    
    if 'route_audit' in blueprints:
        print("   [OK] Blueprint 'route_audit' esta registrado!")
    else:
        print("   [ERRO] Blueprint 'route_audit' NAO esta registrado")
        print(f"   Blueprints encontrados: {', '.join(blueprints)}")
    
    # Contar rotas totais
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    audit_routes = [r for r in routes if r.startswith('/route-audit')]
    
    print(f"   Total de rotas na app: {len(routes)}")
    print(f"   Rotas /route-audit/*: {len(audit_routes)}")
    
    if audit_routes:
        print("\n   Rotas de auditoria disponiveis:")
        for route in audit_routes[:5]:  # Mostrar primeiras 5
            print(f"      - {route}")
        if len(audit_routes) > 5:
            print(f"      ... e mais {len(audit_routes) - 5} rotas")
    
except Exception as e:
    print(f"   [ERRO] ao carregar app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TESTES CONCLUIDOS!")
print("=" * 60)

print("\nPROXIMOS PASSOS:")
print("   1. Se todos os testes passaram, REINICIE a aplicacao:")
print("      python app_pev.py")
print("   2. Acesse: http://localhost:5002/route-audit/")
print("   3. Login: admin@versus.com.br / 123456")
print("\n" + "=" * 60)
