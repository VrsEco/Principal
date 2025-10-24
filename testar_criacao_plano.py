#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from config_database import get_db
from datetime import datetime

print("=" * 70)
print("  TESTANDO CRIAÇÃO DE PLANO")
print("=" * 70)
print()

db = get_db()

# Dados de teste
plan_data = {
    'company_id': 5,  # Use uma company_id que existe
    'name': 'Teste Criação Automática',
    'description': 'Teste',
    'start_date': '2025-11-01',
    'end_date': '2025-12-31',
    'year': 2025,
    'status': 'draft',
    'plan_mode': 'implantacao'
}

print("📋 Tentando criar plano...")
print(f"   Dados: {plan_data}")
print()

try:
    new_plan_id = db.create_plan(plan_data)
    
    if new_plan_id:
        print(f"✅ Plano criado com sucesso! ID: {new_plan_id}")
    else:
        print(f"❌ Falha: create_plan retornou None")
        
except Exception as e:
    print(f"❌ ERRO ao criar plano:")
    print(f"   {e}")
    import traceback
    traceback.print_exc()
    
print()
print("=" * 70)

