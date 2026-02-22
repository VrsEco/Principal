"""Check for class closure before method definition"""

with open("database/postgresql_db.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=" * 60)
print(f"Total de linhas no arquivo: {len(lines)}")
print("=" * 60)

# Procurar por linhas sem indentação (que fechariam a classe) entre 6500 e 6800
print("\nLinhas SEM indentação entre 6500-6800:")
for i in range(6499, min(6800, len(lines))):
    line = lines[i]
    if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
        print(f"  {i+1}: {line[:80].rstrip()}")

# Procurar por definições de classe
print("\nDefinições de classe após linha 6500:")
for i in range(6499, min(6900, len(lines))):
    line = lines[i]
    if "class " in line and "def" not in line:
        print(f"  {i+1}: {line[:80].rstrip()}")

# Mostrar área problema (6770-6810)
print("\nÁrea problemática (6770-6810):")
for i in range(6769, min(6810, len(lines))):
    line = lines[i]
    indent = len(line) - len(line.lstrip())
    marker = "  "
    if indent == 0 and line.strip():
        marker = "🚨"  # Linha sem indentação!
    elif "def get_plan_investment" in line:
        marker = "📍"  # Método alvo
    print(f"{marker} {i+1:5d} [{indent:2d}]: {line[:70].rstrip()}")
