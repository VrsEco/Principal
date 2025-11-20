"""Verify method implementation"""
from database.postgresql_db import PostgreSQLDatabase
import inspect

print("=" * 60)
print("VERIFICAÇÃO DO MÉTODO get_plan_investment_categories")
print("=" * 60)

# Verificar se método existe
has_method = hasattr(PostgreSQLDatabase, "get_plan_investment_categories")
print(f"✓ Método existe na classe: {has_method}")

# Pegar código fonte
src_lines = inspect.getsourcelines(PostgreSQLDatabase.get_plan_investment_categories)
print(f"✓ Linha inicial no arquivo: {src_lines[1]}")
print(f"\nPrimeiras 15 linhas do código:")
print("-" * 60)
for i, line in enumerate(src_lines[0][:15]):
    print(f"{i+1:3d}: {line.rstrip()}")

# Verificar qual classe define o método
defining_class = None
for cls in PostgreSQLDatabase.__mro__:
    if "get_plan_investment_categories" in cls.__dict__:
        defining_class = cls
        break

print(
    f"\n✓ Método definido em: {defining_class.__name__ if defining_class else 'Nenhuma'}"
)

# Testar chamada
print("\n" + "=" * 60)
print("TESTANDO CHAMADA DO MÉTODO")
print("=" * 60)

try:
    from config_database import get_db

    db = get_db()
    result = db.get_plan_investment_categories(8)
    print(f"✅ Sucesso! Resultado: {result}")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback

    traceback.print_exc()
