"""
Script para verificar se as rotas de estruturas estão registradas
"""

import sys
sys.path.insert(0, '.')

from app_pev import app

print("\n🔍 Verificando rotas de estruturas...\n")

structure_routes = [
    ('/pev/api/implantacao/<int:plan_id>/structures', ['POST']),
    ('/pev/api/implantacao/<int:plan_id>/structures/<int:structure_id>', ['GET', 'PUT', 'DELETE']),
]

print("Rotas esperadas:")
for route, methods in structure_routes:
    print(f"  - {route} [{', '.join(methods)}]")

print("\n" + "="*60)
print("Rotas registradas no app:")
print("="*60 + "\n")

found_routes = []
for rule in app.url_map.iter_rules():
    if 'structures' in rule.rule:
        found_routes.append((rule.rule, sorted(rule.methods - {'HEAD', 'OPTIONS'})))
        print(f"✅ {rule.rule}")
        print(f"   Métodos: {', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))}")
        print()

if not found_routes:
    print("❌ NENHUMA rota de estruturas encontrada!")
    print("\n⚠️  AÇÃO NECESSÁRIA: Reiniciar o servidor Flask")
else:
    print(f"✅ {len(found_routes)} rota(s) de estruturas encontrada(s)")
    
print("\n" + "="*60)
print("Diagnóstico:")
print("="*60)

if len(found_routes) < 4:
    print("\n❌ Faltam rotas! Esperado: 4 rotas")
    print("   → Reinicie o servidor Flask: REINICIAR_AGORA.bat")
else:
    print("\n✅ Todas as rotas estão registradas")
    print("   → Se ainda houver erro 404, verifique:")
    print("     1. Servidor está rodando na porta 5003?")
    print("     2. Tentou fazer hard refresh (Ctrl+Shift+R)?")

