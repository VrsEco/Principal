import os
import re

backup_file = r'C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql'

with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print('=== ANÁLISE DO BACKUP ===')
print(f'Tamanho total: {len(content)} caracteres')
print()

# Procurar por diferentes tipos de comandos
patterns = {
    'INSERT INTO': r'INSERT INTO \w+',
    'CREATE TABLE': r'CREATE TABLE \w+',
    'COPY': r'COPY \w+',
    'BEGIN': r'\bBEGIN\b',
    'COMMIT': r'\bCOMMIT\b',
    'SET': r'^SET ',
    'COMMENT': r'^--'
}

for name, pattern in patterns.items():
    matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
    print(f'{name}: {len(matches)} ocorrências')

print()
print('=== PRIMEIRAS 20 LINHAS ===')
lines = content.split('\n')[:20]
for i, line in enumerate(lines, 1):
    print("2d")

print()
print('=== ÚLTIMAS 10 LINHAS ===')
lines = content.split('\n')[-10:]
for i, line in enumerate(lines, 1):
    print("2d")

print()
print('=== PROCURANDO POR DADOS DE USUÁRIOS ===')
# Procurar por diferentes formatos
user_patterns = [
    r'INSERT INTO users',
    r'COPY users',
    r"email.*versus",
    r"versus@gestaoversus"
]

for pattern in user_patterns:
    matches = re.findall(pattern, content, re.IGNORECASE)
    print(f"'{pattern}': {len(matches)} matches")

# Mostrar algumas linhas que contenham "user" ou "email"
print()
print('=== LINHAS CONTENDO "USER" OU "EMAIL" ===')
user_lines = [line for line in content.split('\n') if 'user' in line.lower() or 'email' in line.lower()]
for line in user_lines[:10]:
    print(line[:100] + '...' if len(line) > 100 else line)


