import sqlite3

# Atualizar estrutura do banco de dados
conn = sqlite3.connect("pevapp22.db")
cursor = conn.cursor()

print("=== Atualizando estrutura do banco de dados ===")

# Adicionar colunas na tabela companies
try:
    cursor.execute("ALTER TABLE companies ADD COLUMN legal_name TEXT")
    print("✓ Adicionada coluna legal_name em companies")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna legal_name já existe em companies")
    else:
        print(f"✗ Erro ao adicionar legal_name: {e}")

try:
    cursor.execute("ALTER TABLE companies ADD COLUMN industry TEXT")
    print("✓ Adicionada coluna industry em companies")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna industry já existe em companies")
    else:
        print(f"✗ Erro ao adicionar industry: {e}")

try:
    cursor.execute("ALTER TABLE companies ADD COLUMN size TEXT")
    print("✓ Adicionada coluna size em companies")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna size já existe em companies")
    else:
        print(f"✗ Erro ao adicionar size: {e}")

try:
    cursor.execute("ALTER TABLE companies ADD COLUMN description TEXT")
    print("✓ Adicionada coluna description em companies")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna description já existe em companies")
    else:
        print(f"✗ Erro ao adicionar description: {e}")

# Adicionar colunas na tabela plans
try:
    cursor.execute("ALTER TABLE plans ADD COLUMN description TEXT")
    print("✓ Adicionada coluna description em plans")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna description já existe em plans")
    else:
        print(f"✗ Erro ao adicionar description: {e}")

try:
    cursor.execute("ALTER TABLE plans ADD COLUMN start_date DATE")
    print("✓ Adicionada coluna start_date em plans")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna start_date já existe em plans")
    else:
        print(f"✗ Erro ao adicionar start_date: {e}")

try:
    cursor.execute("ALTER TABLE plans ADD COLUMN end_date DATE")
    print("✓ Adicionada coluna end_date em plans")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✓ Coluna end_date já existe em plans")
    else:
        print(f"✗ Erro ao adicionar end_date: {e}")

conn.commit()
conn.close()

print("\n=== Estrutura atualizada com sucesso! ===")
