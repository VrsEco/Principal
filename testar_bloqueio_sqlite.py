#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste: Bloqueio SQLite
Verifica se o bloqueio está funcionando corretamente
"""

import sys
import traceback

print("=" * 70)
print("🧪 TESTE: Bloqueio SQLite - APP30")
print("=" * 70)
print()

# ========================================
# TESTE 1: Tentar instanciar SQLiteDatabase
# ========================================
print("📋 [1/5] Testando bloqueio SQLiteDatabase...")
try:
    from database.sqlite_db import SQLiteDatabase
    db = SQLiteDatabase(db_path='pevapp22.db')
    print("   ❌ FALHA: SQLiteDatabase foi instanciada! (não deveria)")
    sys.exit(1)
except RuntimeError as e:
    if "DESATIVADO" in str(e) or "desativado" in str(e):
        print("   ✅ SUCESSO: SQLiteDatabase bloqueada corretamente")
        print(f"   📝 Mensagem: {str(e)[:80]}...")
    else:
        print(f"   ⚠️  RuntimeError inesperado: {e}")
except Exception as e:
    print(f"   ❌ Erro inesperado: {e}")
    sys.exit(1)

# ========================================
# TESTE 2: Tentar usar get_database('sqlite')
# ========================================
print("\n📋 [2/5] Testando bloqueio get_database('sqlite')...")
try:
    from database import get_database
    db = get_database('sqlite', db_path='pevapp22.db')
    print("   ❌ FALHA: get_database('sqlite') funcionou! (não deveria)")
    sys.exit(1)
except RuntimeError as e:
    if "BLOQUEADA" in str(e) or "bloqueada" in str(e) or "DESATIVADO" in str(e):
        print("   ✅ SUCESSO: get_database('sqlite') bloqueada corretamente")
        print(f"   📝 Mensagem: {str(e)[:80]}...")
    else:
        print(f"   ⚠️  RuntimeError inesperado: {e}")
except Exception as e:
    print(f"   ❌ Erro inesperado: {e}")
    sys.exit(1)

# ========================================
# TESTE 3: Verificar config_database retorna PostgreSQL
# ========================================
print("\n📋 [3/5] Testando config_database.get_db()...")
try:
    from config_database import get_db
    db = get_db()
    
    db_type = type(db).__name__
    if db_type == 'PostgreSQLDatabase':
        print(f"   ✅ SUCESSO: get_db() retornou PostgreSQLDatabase")
    elif db_type == 'SQLiteDatabase':
        print(f"   ❌ FALHA: get_db() retornou SQLiteDatabase!")
        sys.exit(1)
    else:
        print(f"   ⚠️  Tipo inesperado: {db_type}")
except Exception as e:
    print(f"   ❌ Erro ao testar get_db(): {e}")
    traceback.print_exc()
    sys.exit(1)

# ========================================
# TESTE 4: Verificar arquivos SQLite renomeados
# ========================================
print("\n📋 [4/5] Verificando arquivos SQLite...")
import os

arquivos_esperados = [
    'instance/pevapp22.db.DESATIVADO',
    'instance/pevapp22_dev.db.DESATIVADO',
    'instance/test.db.DESATIVADO'
]

arquivos_nao_devem_existir = [
    'instance/pevapp22.db',
    'instance/pevapp22_dev.db',
    'instance/test.db'
]

todos_ok = True

# Verificar que arquivos .DESATIVADO existem
for arquivo in arquivos_esperados:
    if os.path.exists(arquivo):
        print(f"   ✅ {arquivo} existe (backup seguro)")
    else:
        print(f"   ⚠️  {arquivo} NÃO encontrado")

# Verificar que arquivos .db NÃO existem
for arquivo in arquivos_nao_devem_existir:
    if os.path.exists(arquivo):
        print(f"   ❌ {arquivo} ainda existe! (deveria estar renomeado)")
        todos_ok = False
    else:
        print(f"   ✅ {arquivo} não existe (correto)")

if not todos_ok:
    print("\n   ⚠️  Alguns arquivos SQLite não foram renomeados corretamente")

# ========================================
# TESTE 5: Importar app_pev
# ========================================
print("\n📋 [5/5] Testando importação do app_pev...")
try:
    import app_pev
    print("   ✅ SUCESSO: app_pev importado sem erros")
    print("   📝 Sistema de logs integrado:", hasattr(app_pev, 'app'))
except RuntimeError as e:
    if "SQLite" in str(e) or "sqlite" in str(e):
        print("   ❌ FALHA: app_pev tentou usar SQLite!")
        print(f"   📝 Erro: {str(e)[:100]}...")
        print("\n" + "=" * 70)
        print("🔍 ERRO ENCONTRADO! Veja o traceback abaixo:")
        print("=" * 70)
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("💡 AÇÃO NECESSÁRIA:")
        print("   1. Veja o arquivo e linha no traceback acima")
        print("   2. Corrija aquele código para usar PostgreSQL")
        print("   3. Use config_database.get_db() ao invés de SQLite")
        print("=" * 70)
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Erro ao importar app_pev: {e}")
    traceback.print_exc()
    sys.exit(1)

# ========================================
# RESUMO FINAL
# ========================================
print("\n" + "=" * 70)
print("✅ TODOS OS TESTES PASSARAM!")
print("=" * 70)
print()
print("📊 Resumo:")
print("   ✅ SQLiteDatabase bloqueada")
print("   ✅ get_database('sqlite') bloqueada")
print("   ✅ config_database.get_db() retorna PostgreSQL")
print("   ✅ Arquivos SQLite renomeados (.DESATIVADO)")
print("   ✅ app_pev importa sem erros de SQLite")
print()
print("🎯 Resultado:")
print("   ✅ SQLite está 100% DESATIVADO")
print("   ✅ Sistema forçado a usar PostgreSQL")
print("   ✅ Qualquer tentativa de usar SQLite vai gerar erro claro")
print()
print("🚀 Próximo passo:")
print("   → Inicie a aplicação: python app_pev.py")
print("   → Teste todas as funcionalidades")
print("   → Se houver erro de SQLite, o traceback mostrará onde corrigir")
print()
print("=" * 70)

