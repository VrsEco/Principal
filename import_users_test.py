import sys
import os
import re

print("🧪 TESTE: Análise de usuários no backup")

backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

if not os.path.exists(backup_file):
    print(f"❌ Arquivo não encontrado: {backup_file}")
    sys.exit(1)

# Ler backup
with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print(f"✅ Arquivo lido: {len(content)} caracteres")

# Procurar dados de usuários
copy_pattern = r'COPY (?:public\.)?users\s*\((.*?)\)\s*FROM stdin;(.*?)(?=COPY|\Z)'
match = re.search(copy_pattern, content, re.IGNORECASE | re.DOTALL)

if not match:
    print("❌ Nenhum bloco COPY de usuários encontrado")
    sys.exit(1)

columns_str, data_block = match.groups()
columns = [col.strip() for col in columns_str.split(',')]

print(f"📋 Colunas encontradas: {columns}")

# Extrair linhas de dados
data_lines = []
for line in data_block.split('\n'):
    line = line.strip()
    if line == '\\.' or not line:
        break
    if line:
        data_lines.append(line)

print(f"👥 Usuários encontrados: {len(data_lines)}")

# Mostrar primeiros usuários
print("\n👀 Primeiros usuários:")
for i, line in enumerate(data_lines[:5]):
    values = line.split('\t')
    if len(values) >= 3:
        user_id = values[0]
        email = values[1] if len(values) > 1 else "?"
        name = values[2] if len(values) > 2 else "?"
        print(f"  {i+1}. ID:{user_id} | {email} | {name}")

print("\n✅ Teste concluído! Dados podem ser importados.")


