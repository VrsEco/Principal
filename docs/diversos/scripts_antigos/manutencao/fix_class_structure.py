"""Fix class structure by moving functions to end of file"""

# Ler o arquivo
with open('database/postgresql_db.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total de linhas: {len(lines)}")

# Encontrar funções sem indentação entre linha 6506 e 7000
functions_to_move = []
current_function = []
in_function = False
start_line = None

for i in range(6505, len(lines)):  # A partir da linha 6506 (índice 6505)
    line = lines[i]
    indent = len(line) - len(line.lstrip())
    
    # Se encontrar uma função sem indentação
    if indent == 0 and line.strip().startswith('def '):
        if in_function and current_function:
            # Salvar função anterior
            functions_to_move.append({
                'start': start_line,
                'end': i - 1,
                'lines': current_function
            })
        # Iniciar nova função
        in_function = True
        start_line = i
        current_function = [line]
    elif in_function:
        # Se linha tem indentação ou é vazia, faz parte da função
        if indent > 0 or not line.strip():
            current_function.append(line)
        else:
            # Linha sem indentação e não é def = fim da função
            if current_function:
                functions_to_move.append({
                    'start': start_line,
                    'end': i - 1,
                    'lines': current_function
                })
            in_function = False
            current_function = []
            start_line = None

# Se ainda tem função em andamento
if in_function and current_function:
    functions_to_move.append({
        'start': start_line,
        'end': len(lines) - 1,
        'lines': current_function
    })

print(f"\nFunções encontradas: {len(functions_to_move)}")
for func in functions_to_move:
    first_line = func['lines'][0].strip()
    print(f"  - Linha {func['start']+1}: {first_line[:60]}")

# Remover linhas das funções
lines_to_remove = set()
for func in functions_to_move:
    for i in range(func['start'], func['end'] + 1):
        lines_to_remove.add(i)

# Criar novo conteúdo
new_lines = []
for i, line in enumerate(lines):
    if i not in lines_to_remove:
        new_lines.append(line)

# Adicionar funções no final
new_lines.append('\n')
new_lines.append('# ============================================================\n')
new_lines.append('# HELPER FUNCTIONS (moved from inside class)\n')
new_lines.append('# ============================================================\n')
new_lines.append('\n')

for func in functions_to_move:
    new_lines.extend(func['lines'])
    new_lines.append('\n')

# Salvar backup
import shutil
shutil.copy2('database/postgresql_db.py', 'database/postgresql_db.py.backup')
print(f"\n✅ Backup criado: database/postgresql_db.py.backup")

# Salvar novo arquivo
with open('database/postgresql_db.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"✅ Arquivo corrigido!")
print(f"   Linhas originais: {len(lines)}")
print(f"   Linhas removidas: {len(lines_to_remove)}")
print(f"   Linhas finais: {len(new_lines)}")
print(f"   Funções movidas para o final: {len(functions_to_move)}")

