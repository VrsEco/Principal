import os
import re

backup_file = r'C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql'
print('Arquivo existe:', os.path.exists(backup_file))

if os.path.exists(backup_file):
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    print('Tamanho:', len(content))

    # Procurar por INSERT INTO users
    matches = re.findall(r'INSERT INTO users .*?;', content, re.IGNORECASE | re.DOTALL)
    print('Usuários encontrados:', len(matches))

    if matches:
        print('Primeiro INSERT (100 chars):', matches[0][:100])
        print('...')

    # Procurar por companies
    matches_companies = re.findall(r'INSERT INTO companies .*?;', content, re.IGNORECASE | re.DOTALL)
    print('Empresas encontradas:', len(matches_companies))

else:
    print('Arquivo não encontrado')














