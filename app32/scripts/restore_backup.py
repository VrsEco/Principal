"""
Script para restaurar backup SQL no banco bd_app_versus
"""
import os
import sys
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# --- TRAVA DE SEGURANÇA ---
ENVIRONMENT = os.getenv("FLASK_ENV", "development")
if ENVIRONMENT == "production":
    print("❌ ERRO CRÍTICO: Este script não pode ser executado em ambiente de PRODUÇÃO.")
    sys.exit(1)

confirm = input("⚠️  ATENÇÃO: Você está prestes a restaurar dados de teste. Isso sobrescreverá registros atuais. Continuar? (S/N): ")
if confirm.upper() != 'S':
    print("Operação cancelada.")
    sys.exit(0)
# ---------------------------

backup_file = r"C:\GestaoVersus\app31\export_20251221_full.sql"

if not os.path.exists(backup_file):
    print(f"❌ Arquivo de backup não encontrado: {backup_file}")
    exit(1)

print(f"Lendo backup de: {backup_file}")
print(f"Tamanho: {os.path.getsize(backup_file) / 1024 / 1024:.2f} MB")

password = quote_plus("*Paraiso1978")
url = f"postgresql://postgres:{password}@localhost:5432/bd_app_versus"
engine = create_engine(url, isolation_level="AUTOCOMMIT")

print("\nConectando ao banco bd_app_versus...")

with open(backup_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

print(f"Backup lido: {len(sql_content)} caracteres")

# Dividir em statements individuais
statements = []
current_statement = []
in_copy = False

for line in sql_content.split('\n'):
    # Detectar início de COPY
    if line.strip().startswith('COPY '):
        in_copy = True
        current_statement.append(line)
        continue
    
    # Detectar fim de COPY
    if in_copy and line.strip() == '\\.':
        current_statement.append(line)
        statements.append('\n'.join(current_statement))
        current_statement = []
        in_copy = False
        continue
    
    # Dentro de COPY, adicionar linha
    if in_copy:
        current_statement.append(line)
        continue
    
    # Fora de COPY, processar normalmente
    current_statement.append(line)
    
    # Se termina com ; e não está vazio, é um statement completo
    if line.strip().endswith(';') and not in_copy:
        stmt = '\n'.join(current_statement)
        if stmt.strip():
            statements.append(stmt)
        current_statement = []

# Adicionar último statement se houver
if current_statement:
    stmt = '\n'.join(current_statement)
    if stmt.strip():
        statements.append(stmt)

print(f"\nTotal de statements: {len(statements)}")
print("\nExecutando restore...")

with engine.connect() as conn:
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements, 1):
        stmt_preview = statement[:100].replace('\n', ' ')
        
        # Pular comentários e linhas vazias
        if not statement.strip() or statement.strip().startswith('--'):
            continue
        
        try:
            conn.execute(text(statement))
            success_count += 1
            if i % 100 == 0:
                print(f"  Progresso: {i}/{len(statements)} statements")
        except Exception as e:
            error_count += 1
            error_msg = str(e)[:100]
            # Ignorar alguns erros esperados
            if 'already exists' in error_msg or 'does not exist' in error_msg:
                continue
            print(f"  ⚠ Statement {i}: {error_msg}")

print(f"\n✅ Restore concluído!")
print(f"   Sucesso: {success_count}")
print(f"   Erros: {error_count}")
