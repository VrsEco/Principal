#!/usr/bin/env python3
"""
Debug do formato do backup
"""
import sys
import os
import re

backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("🔍 ANÁLISE DETALHADA DO BACKUP")
print("=" * 50)
print(f"Tamanho total: {len(content)} caracteres")
print()

# Procurar por diferentes padrões
patterns = [
    (r'COPY \w+', 'Comandos COPY'),
    (r'INSERT INTO \w+', 'Comandos INSERT'),
    (r'CREATE TABLE \w+', 'Criação de tabelas'),
    (r'\\\.[\r\n]', 'Fim de bloco COPY'),
    (r'SET \w+', 'Comandos SET'),
    (r'--', 'Comentários')
]

for pattern, description in patterns:
    matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
    print("4d")

print()
print("📄 PRIMEIRAS 10 LINHAS:")
print("-" * 30)
lines = content.split('\n')[:10]
for i, line in enumerate(lines, 1):
    print("2d")

print()
print("🔍 PROCURANDO POR BLOCOS COPY:")
print("-" * 30)

# Procurar por blocos COPY completos
copy_blocks = re.findall(r'COPY .*?FROM stdin;.*?\\\.', content, re.IGNORECASE | re.DOTALL)
print(f"Encontrados {len(copy_blocks)} blocos COPY completos")

if copy_blocks:
    print("\n📋 Primeiro bloco COPY:")
    first_block = copy_blocks[0]
    print(first_block[:200] + "..." if len(first_block) > 200 else first_block)

    # Extrair nome da tabela
    table_match = re.search(r'COPY (\w+)', first_block, re.IGNORECASE)
    if table_match:
        print(f"\n🏷️  Tabela: {table_match.group(1)}")

        # Contar linhas de dados
        lines_in_block = first_block.split('\n')
        data_start = False
        data_lines = 0
        for line in lines_in_block:
            if 'FROM stdin;' in line:
                data_start = True
                continue
            if data_start and line.strip() and not line.startswith('\\'):
                data_lines += 1

        print(f"📊 Linhas de dados: {data_lines}")
else:
    print("❌ Nenhum bloco COPY encontrado!")











