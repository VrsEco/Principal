"""Debug class structure"""
import inspect
from database.postgresql_db import PostgreSQLDatabase

print("=" * 60)
print("ANÁLISE DA CLASSE PostgreSQLDatabase")
print("=" * 60)

# Encontrar todas as definições de get_plan_investment_categories no arquivo
import re

with open("database/postgresql_db.py", "r", encoding="utf-8") as f:
    content = f.read()
    lines = content.split("\n")

    # Procurar por definições do método
    for i, line in enumerate(lines, 1):
        if "def get_plan_investment_categories" in line:
            # Contar indentação
            indent = len(line) - len(line.lstrip())
            print(f"\nLinha {i}: {line[:80]}")
            print(f"  Indentação: {indent} espaços")

            # Mostrar linhas ao redor
            print(f"  Contexto (5 linhas antes):")
            for j in range(max(0, i - 6), i - 1):
                print(f"    {j+1}: {lines[j][:80]}")

# Verificar quais classes têm o método
print("\n" + "=" * 60)
print("CLASSES COM O MÉTODO")
print("=" * 60)

for cls in PostgreSQLDatabase.__mro__:
    if "get_plan_investment_categories" in cls.__dict__:
        print(f"  ✓ {cls.__name__}")
        method = cls.__dict__["get_plan_investment_categories"]
        try:
            src = inspect.getsource(method)
            print(f"    Primeiras 3 linhas:")
            for line in src.split("\n")[:3]:
                print(f"      {line}")
        except:
            print(f"    Não foi possível obter código-fonte")

print("\n" + "=" * 60)
print("VERIFICAÇÃO FINAL")
print("=" * 60)

# Tentar chamar o método diretamente da classe
try:
    instance = PostgreSQLDatabase(
        host="localhost",
        port=5432,
        database="bd_app_versus",
        user="postgres",
        password="*Paraiso1978",
    )
    result = instance.get_plan_investment_categories(8)
    print(f"✅ Sucesso! Resultado: {result}")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback

    traceback.print_exc()
